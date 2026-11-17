import hashlib
import hmac
import json
import tempfile
import time
import unittest
from unittest.mock import patch
import httpx

from kurt.billing.ledger import Wallet
from kurt.billing.payments import Payments
from kurt.billing import WalletError


class PaymentTests(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        self.tmp=tempfile.TemporaryDirectory();self.addCleanup(self.tmp.cleanup)
        self.wallet=Wallet(self.tmp.name);self.tenant,self.token=self.wallet.grant('pro')
        self.payments=Payments(self.wallet,'sk_test_fixture','whsec_fixture',return_url='https://kurt.example/wallet')
        with self.wallet.transaction() as db:
            db.execute("INSERT INTO wallet_topups(id,tenant,cents,session,state) VALUES('order',?,1000,'cs_fixture','pending')",(self.tenant,))

    def send(self,kind,obj,event_id='evt_fixture',live=False,stamp=None):
        raw=json.dumps({'id':event_id,'livemode':live,'type':kind,'data':{'object':obj}}).encode()
        stamp=stamp or int(time.time())
        signature=hmac.new(b'whsec_fixture',str(stamp).encode()+b'.'+raw,hashlib.sha256).hexdigest()
        return self.payments.event(raw,f't={stamp},v1={signature}')

    def paid(self):
        return {'id':'cs_fixture','mode':'payment','payment_status':'paid','currency':'usd','amount_total':1000,
                'payment_intent':'pi_fixture','client_reference_id':'order','metadata':{'kurt_topup_id':'order'}}

    def test_signed_paid_topup_credits_exact_amount_once_across_distinct_events(self):
        self.send('checkout.session.completed',self.paid())
        self.send('checkout.session.completed',self.paid())
        self.send('checkout.session.async_payment_succeeded',self.paid(),'evt_async')
        self.assertEqual(self.wallet.summary(self.tenant)['balance_usd'],'10')
        self.assertEqual(len(self.wallet.history(self.tenant)['entries']),1)

    def test_same_signed_business_event_with_different_delivery_metadata_is_idempotent(self):
        self.send('checkout.session.completed',self.paid())
        raw=json.dumps({'pending_webhooks':0,'id':'evt_fixture','livemode':False,'type':'checkout.session.completed','data':{'object':self.paid()}},sort_keys=True,indent=2).encode()
        stamp=str(int(time.time()))
        signature=hmac.new(b'whsec_fixture',stamp.encode()+b'.'+raw,hashlib.sha256).hexdigest()
        self.assertTrue(self.payments.event(raw,f't={stamp},v1={signature}')['duplicate'])
        self.assertEqual(self.wallet.summary(self.tenant)['balance_usd'],'10')

    def test_unpaid_redirect_unrecognized_signature_and_wrong_environment_do_not_credit(self):
        value=self.paid();value['payment_status']='unpaid'
        self.send('checkout.session.completed',value)
        with self.assertRaises(WalletError):self.payments.event(b'{}','t=1,v1=forged')
        with self.assertRaises(WalletError):self.send('checkout.session.completed',self.paid(),live=True)
        with self.assertRaises(WalletError):self.send('checkout.session.completed',self.paid(),stamp=int(time.time())-1000)
        self.assertEqual(self.wallet.summary(self.tenant)['balance_usd'],'0')

    def test_valid_timestamp_with_forged_signature_or_modified_raw_body_is_rejected(self):
        raw=json.dumps({'id':'evt_forged','livemode':False,'type':'checkout.session.completed','data':{'object':self.paid()}}).encode()
        stamp=str(int(time.time()))
        signature=hmac.new(b'whsec_fixture',stamp.encode()+b'.'+raw,hashlib.sha256).hexdigest()
        with self.assertRaises(WalletError):self.payments.event(raw+b' ',f't={stamp},v1={signature}')
        with self.assertRaises(WalletError):self.payments.event(raw,f't={stamp},v1='+('0'*64))
        self.assertEqual(self.wallet.summary(self.tenant)['balance_usd'],'0')

    def test_amount_currency_session_and_tenant_reference_must_match_server_order(self):
        for field,value in [('amount_total',9999),('currency','php'),('id','cs_other'),('client_reference_id','other'),('mode','subscription')]:
            item=self.paid();item[field]=value
            with self.subTest(field=field),self.assertRaises(WalletError):self.send('checkout.session.completed',item)
        self.assertEqual(self.wallet.summary(self.tenant)['balance_usd'],'0')

    def test_partial_refunds_cumulative_replay_and_post_spend_debt(self):
        self.send('checkout.session.completed',self.paid())
        identity=self.wallet.auth(self.token)
        request=self.wallet.reserve_money(identity,'openrouter','m','1','x','x')
        self.wallet.settle(self.tenant,request,'8',basis='receipt',evidence='bill')
        obj={'payment_intent':'pi_fixture','currency':'usd','amount_refunded':500}
        self.send('charge.refunded',obj,'evt_refund')
        self.send('charge.refunded',obj,'evt_refund')
        self.send('charge.refunded',obj,'evt_second_refund_event')
        self.assertEqual(self.wallet.summary(self.tenant)['balance_usd'],'-3')
        with self.assertRaises(WalletError):self.wallet.reserve_money(identity,'openrouter','m','1','next','next')

    def test_dispute_won_restores_only_non_refunded_credit(self):
        self.send('checkout.session.completed',self.paid())
        self.send('charge.dispute.created',{'id':'dp_fixture','payment_intent':'pi_fixture','currency':'usd','amount':1000},'evt_dispute')
        self.send('charge.refunded',{'payment_intent':'pi_fixture','currency':'usd','amount_refunded':300},'evt_refund')
        self.assertEqual(self.wallet.summary(self.tenant)['balance_usd'],'0')
        self.send('charge.dispute.closed',{'id':'dp_fixture','payment_intent':'pi_fixture','currency':'usd','status':'won'},'evt_won')
        self.assertEqual(self.wallet.summary(self.tenant)['balance_usd'],'7')

    def test_out_of_order_refund_is_retriable_not_silently_ignored(self):
        with self.assertRaises(WalletError) as error:
            self.send('charge.refunded',{'payment_intent':'pi_fixture','currency':'usd','amount_refunded':1000},'evt_early')
        self.assertEqual(error.exception.status,409)

    async def test_checkout_is_server_priced_and_does_not_credit_before_webhook(self):
        calls=[];real=httpx.AsyncClient
        def handler(request):
            calls.append(request)
            return httpx.Response(200,json={'id':'cs_new','url':'https://checkout.stripe.com/c/pay/fixture'})
        with patch('kurt.billing.payments.httpx.AsyncClient',lambda **kw:real(transport=httpx.MockTransport(handler),**kw)):
            result=await self.payments.checkout(self.tenant,2500)
        self.assertEqual(result['amount_usd'],'25')
        self.assertEqual(calls[0].url.host,'api.stripe.com')
        self.assertIn(b'unit_amount%5D=2500',calls[0].content)
        self.assertEqual(self.wallet.summary(self.tenant)['balance_usd'],'0')

    async def test_unconfigured_processor_cannot_simulate_successful_topup(self):
        with self.assertRaises(WalletError):await Payments(self.wallet,'','').checkout(self.tenant,1000)
