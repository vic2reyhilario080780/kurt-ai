"""Stripe Checkout top-ups. Credit only a signed, paid, server-matched order."""
import hashlib
import hmac
import json
import time
import uuid
from decimal import Decimal
import httpx

from . import WalletError
from .ledger import SCALE


class Payments:
    def __init__(self, wallet, key, webhook_secret, *, live=False, return_url=''):
        self.wallet, self._key, self._secret = wallet, key, webhook_secret
        self.live, self.return_url = live, return_url

    @property
    def enabled(self):
        return bool(self._key and self._secret and self.return_url)

    async def checkout(self, tenant, cents):
        if not self.enabled: raise WalletError('payment_processor_not_configured', 503)
        if type(cents) is not int or not 100 <= cents <= 100000: raise ValueError('Top-up must be $1 to $1,000 USD.')
        from kurt.utils.security import require_secure_endpoint
        require_secure_endpoint(self.return_url)
        identity = str(uuid.uuid4())
        with self.wallet.transaction() as db:
            self.wallet._account(db, tenant)
            db.execute("INSERT INTO wallet_topups(id,tenant,cents,state) VALUES(?,?,?,'created')", (identity,tenant,cents))
        form = {'mode':'payment', 'success_url':self.return_url, 'cancel_url':self.return_url,
                'client_reference_id':identity, 'metadata[kurt_topup_id]':identity,
                'line_items[0][quantity]':'1', 'line_items[0][price_data][currency]':'usd',
                'line_items[0][price_data][unit_amount]':str(cents),
                'line_items[0][price_data][product_data][name]':'Kurt Wallet credits (USD)'}
        try:
            async with httpx.AsyncClient(timeout=20,follow_redirects=False,trust_env=False) as client:
                response = await client.post('https://api.stripe.com/v1/checkout/sessions', data=form,
                    headers={'Authorization':'Bearer '+self._key,'Idempotency-Key':'kurt-topup-'+identity})
                response.raise_for_status(); result = response.json()
            session, url = result['id'], result['url']
            from urllib.parse import urlsplit
            parsed = urlsplit(url)
            if parsed.scheme != 'https' or parsed.hostname != 'checkout.stripe.com' or parsed.username or parsed.password or parsed.port not in (None,443):
                raise ValueError('Invalid checkout destination.')
            if not isinstance(session,str) or not session.startswith('cs_'): raise ValueError('Invalid checkout session.')
            with self.wallet.transaction() as db:
                db.execute("UPDATE wallet_topups SET session=?,state='pending' WHERE id=?", (session,identity))
            return {'checkout_url':url,'topup_id':identity,'amount_usd':format(Decimal(cents)/100,'f'),'currency':'USD','markup_percent':0}
        except Exception:
            # Never credit a browser redirect, client claim or an ambiguous call.
            raise WalletError('checkout_not_confirmed',503) from None

    def event(self, raw, signature):
        if not self._secret: raise WalletError('payment_processor_not_configured',503)
        if not isinstance(signature,str) or len(signature)>2048: raise WalletError('invalid_webhook',400)
        parts = [p.split('=',1) for p in signature.split(',') if '=' in p]
        stamps = [v for k,v in parts if k=='t']
        if len(stamps)!=1: raise WalletError('invalid_webhook',400)
        if not stamps[0].isascii() or not stamps[0].isdigit() or len(stamps[0])>12: raise WalletError('invalid_webhook',400)
        try: stamp=int(stamps[0])
        except ValueError: raise WalletError('invalid_webhook',400) from None
        if abs(time.time()-stamp)>300: raise WalletError('stale_webhook',400)
        expected=hmac.new(self._secret.encode(),stamps[0].encode()+b'.'+raw,hashlib.sha256).hexdigest()
        if not any(hmac.compare_digest(expected,v) for k,v in parts if k=='v1'):
            raise WalletError('invalid_webhook',400)
        from kurt.saas.protocol import decode
        event=decode(raw)
        if not isinstance(event.get('id'),str) or not event['id'].startswith('evt_') or event.get('livemode') is not self.live:
            raise WalletError('wrong_payment_environment',400)
        kind=event.get('type'); obj=(event.get('data') or {}).get('object')
        if not isinstance(obj,dict): raise WalletError('invalid_webhook',400)
        # Signature validation uses raw bytes; idempotency uses stable business
        # content so delivery metadata/JSON formatting cannot double-credit.
        digest=hashlib.sha256(json.dumps({'id':event['id'],'live':event['livemode'],'type':kind,'object':obj},sort_keys=True,separators=(',',':')).encode()).hexdigest()
        supported={'checkout.session.completed','checkout.session.async_payment_succeeded','charge.refunded','charge.dispute.created','charge.dispute.closed'}
        if kind not in supported: return {'received':True,'ignored':True}
        with self.wallet.transaction() as db:
            old=db.execute('SELECT digest FROM wallet_payment_events WHERE id=?',(event['id'],)).fetchone()
            if old:
                if old[0]!=digest: raise WalletError('webhook_replay_conflict',400)
                return {'received':True,'duplicate':True}
            if kind.startswith('checkout.session.'):
                reference=(obj.get('metadata') or {}).get('kurt_topup_id')
                row=db.execute('SELECT * FROM wallet_topups WHERE id=? AND session=?',(reference,obj.get('id'))).fetchone()
                if not row: raise WalletError('unknown_topup',400)
                # completion can precede asynchronous payment confirmation.
                if obj.get('payment_status')!='paid': return {'received':True,'pending':True}
                if obj.get('mode')!='payment' or obj.get('currency')!='usd' or type(obj.get('amount_total')) is not int or obj['amount_total']!=row['cents'] or obj.get('client_reference_id')!=row['id']:
                    raise WalletError('payment_amount_mismatch',400)
                intent=obj.get('payment_intent')
                if not isinstance(intent,str) or not intent.startswith('pi_'): raise WalletError('invalid_payment_intent',400)
                if row['intent'] and row['intent']!=intent: raise WalletError('payment_identity_mismatch',400)
                self.wallet._entry(db,row['tenant'],row['cents']*SCALE//100,'stripe:'+row['session'],'payment_credit')
                db.execute("UPDATE wallet_topups SET state='paid',intent=? WHERE id=?",(intent,row['id']))
            else:
                intent=obj.get('payment_intent')
                row=db.execute('SELECT * FROM wallet_topups WHERE intent=?',(intent,)).fetchone()
                # Out-of-order refunds/disputes must retry after paid top-up.
                if not row or row['state']!='paid': raise WalletError('payment_not_recorded_yet',409)
                if obj.get('currency')!='usd': raise WalletError('payment_currency_mismatch',400)
                refunded,disputed=row['refunded'],row['disputed']
                if kind=='charge.refunded':
                    amount=obj.get('amount_refunded')
                    if type(amount) is not int or not 0<=amount<=row['cents']: raise WalletError('invalid_refund',400)
                    refunded=max(refunded,amount)
                elif kind=='charge.dispute.created':
                    amount=obj.get('amount')
                    if type(amount) is not int or not 0<=amount<=row['cents'] or not isinstance(obj.get('id'),str): raise WalletError('invalid_dispute',400)
                    if row['dispute_id'] not in (None,obj['id']): raise WalletError('dispute_conflict',400)
                    disputed=amount
                    db.execute('UPDATE wallet_topups SET dispute_id=? WHERE id=?',(obj['id'],row['id']))
                else:
                    if obj.get('id')!=row['dispute_id']: raise WalletError('dispute_not_recorded_yet',409)
                    if obj.get('status')=='won': disputed=0
                    elif obj.get('status')!='lost': return {'received':True,'pending':True}
                # Refunds and disputes cannot reverse the same credit twice.
                target=min(row['cents'],refunded+disputed)
                delta=(row['applied_reversal']-target)*SCALE//100
                self.wallet._entry(db,row['tenant'],delta,'stripe-event:'+event['id'],'payment_adjustment')
                db.execute('UPDATE wallet_topups SET refunded=?,disputed=?,applied_reversal=? WHERE id=?', (refunded,disputed,target,row['id']))
            db.execute('INSERT INTO wallet_payment_events VALUES(?,?,?)',(event['id'],digest,time.time()))
        return {'received':True}
