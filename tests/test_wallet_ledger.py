from concurrent.futures import ThreadPoolExecutor
import json
import tempfile
import unittest
from unittest.mock import patch
from pathlib import Path
from decimal import Decimal

from kurt.billing import WalletError
from kurt.billing.ledger import Wallet,units,usd


class WalletLedgerTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory();self.addCleanup(self.tmp.cleanup)
        self.wallet=Wallet(self.tmp.name)
        self.tenant,self.token=self.wallet.grant('pro')
        self.identity=self.wallet.auth(self.token)

    def fund(self,value='10'):
        self.wallet.manual_credit(self.tenant,value,'first','Personal testing; not a purchase')

    def reserve(self,key='request',hold='1',identity=None):
        return self.wallet.reserve_money(identity or self.identity,'openrouter','fixture/model',hold,key,'fingerprint')

    def test_precise_decimal_money_never_float_or_markup(self):
        self.assertEqual(units('0.000000000001'),1)
        self.assertEqual(usd(units('1.000000123456')),'1.000000123456')
        for bad in (0.1,True,'NaN','Infinity','-1','0.0000000000001','1000001'):
            with self.subTest(bad=bad),self.assertRaises(ValueError):units(bad)
        self.assertEqual(self.wallet.summary(self.tenant)['markup_percent'],0)
        self.assertEqual(self.wallet.summary(self.tenant)['balance_usd'],'0')

    def test_manual_credit_is_idempotent_and_auditable(self):
        self.fund();self.fund()
        self.assertEqual(self.wallet.summary(self.tenant)['balance_usd'],'10')
        entry=self.wallet.history(self.tenant)['entries'][0]
        self.assertEqual(entry['kind'],'manual_credit');self.assertIn('not a purchase',entry['note'])
        with self.assertRaises(WalletError):self.wallet.manual_credit(self.tenant,'11','first','test')

    def test_atomic_reservations_cannot_overspend(self):
        self.fund('1')
        def attempt(index):
            try:return self.reserve(str(index),'0.6')
            except WalletError:return None
        with ThreadPoolExecutor(max_workers=8) as pool:results=list(pool.map(attempt,range(8)))
        self.assertEqual(sum(value is not None for value in results),1)
        self.assertEqual(self.wallet.summary(self.tenant)['available_usd'],'0.4')

    def test_pending_hold_survives_restart_without_assuming_zero_cost(self):
        self.fund();request=self.reserve()
        self.wallet.submitted(self.tenant,request);self.wallet.pending(self.tenant,request)
        restarted=Wallet(self.tmp.name)
        self.assertEqual(restarted.summary(self.tenant)['reserved_usd'],'1')
        self.assertIsNone(restarted.request(self.tenant,request)['cost'])
        self.assertEqual(restarted.summary(self.tenant)['balance_usd'],'10')

    def test_exact_cost_and_zero_are_valid_and_cannot_double_charge(self):
        self.fund();request=self.reserve()
        self.wallet.record(self.tenant,request,provider_id='gen-1',usage={'input_tokens':10,'output_tokens':2})
        self.wallet.settle(self.tenant,request,'0.000000123456',basis='provider_receipt',evidence='gen-1')
        self.assertFalse(self.wallet.settle(self.tenant,request,'0.000000123456',basis='provider_receipt',evidence='gen-1'))
        self.assertEqual(self.wallet.summary(self.tenant)['available_usd'],'9.999999876544')
        second=self.reserve('second');self.wallet.settle(self.tenant,second,'0',basis='provider_receipt',evidence='gen-free')
        self.assertEqual(self.wallet.summary(self.tenant)['reserved_usd'],'0')
        with self.assertRaises(WalletError):self.wallet.settle(self.tenant,request,'1',basis='bad',evidence='other')

    def test_actual_cost_exceeding_hold_is_recorded_and_freezes_further_spend(self):
        self.fund('1');request=self.reserve()
        self.wallet.settle(self.tenant,request,'1.2',basis='provider_receipt',evidence='bill')
        self.assertEqual(self.wallet.summary(self.tenant)['balance_usd'],'-0.2')
        with self.assertRaises(WalletError):self.reserve('another')

    def test_tenant_ownership_and_provider_resource_boundaries(self):
        self.fund();request=self.reserve()
        other,token=self.wallet.grant('pro')
        with self.assertRaises(WalletError):self.wallet.request(other,request)
        with self.assertRaises(WalletError):self.wallet.settle(other,request,'1',basis='bad',evidence='bad')
        self.wallet.add_resource(self.tenant,'replicate','prediction',request)
        with self.assertRaises(WalletError):self.wallet.resource(other,'replicate','prediction')
        self.wallet.add_resource(self.tenant,'replicate-version','version','owner/model')
        self.wallet.add_resource(other,'replicate-version','version','owner/model')
        self.assertEqual(self.wallet.resource(other,'replicate-version','version')['request_id'],'owner/model')

    def test_session_provider_budget_expiry_and_revocation(self):
        self.fund()
        token=self.wallet.session(self.token,'openrouter','fixture',budget='1')
        identity=self.wallet.auth(token)
        self.reserve('one','0.6',identity)
        with self.assertRaises(WalletError):self.reserve('two','0.6',identity)
        with self.assertRaises(WalletError):self.wallet.reserve_money(identity,'mistral','m','0.1','x','x')
        with self.assertRaises(WalletError):self.wallet.session(token,'openrouter','fixture')
        self.wallet.revoke(self.tenant)
        with self.assertRaises(WalletError):self.wallet.auth(token)
        self.wallet.grant('pro',tenant=self.tenant)
        with self.assertRaises(WalletError):self.wallet.auth(token)
        self.assertEqual(self.wallet.summary(self.tenant)['reserved_usd'],'0.6')
        self.assertNotIn(token.encode(),self.wallet.path.read_bytes())

    def test_duplicate_request_never_replays_even_after_settlement(self):
        self.fund();request=self.reserve()
        self.wallet.settle(self.tenant,request,'0',basis='provider_receipt',evidence='free')
        with self.assertRaisesRegex(WalletError,'not_replayed'):self.reserve()

    def test_invoice_correction_is_append_only_and_cannot_replay_stale_cost(self):
        self.fund();request=self.reserve()
        self.wallet.settle(self.tenant,request,'1',basis='provider_receipt',evidence='initial')
        self.wallet.correct(self.tenant,request,'0.8',evidence='invoice-1')
        self.assertFalse(self.wallet.correct(self.tenant,request,'0.8',evidence='invoice-1'))
        self.wallet.correct(self.tenant,request,'0.9',evidence='invoice-2')
        with self.assertRaises(WalletError):self.wallet.correct(self.tenant,request,'0.8',evidence='invoice-1')
        self.assertEqual(self.wallet.summary(self.tenant)['balance_usd'],'9.1')
        self.assertEqual(len(self.wallet.history(self.tenant)['entries']),4)

    def test_usage_records_contain_no_prompts_or_credentials(self):
        self.fund();request=self.reserve()
        self.wallet.record(self.tenant,request,usage={'input_tokens':10,'output_tokens':3,'prompt':'PRIVATE','api_key':'SECRET'})
        row=self.wallet.request(self.tenant,request)
        self.assertEqual(json.loads(row['usage']),{'input_tokens':10,'output_tokens':3})
        self.assertNotIn(self.token.encode(),self.wallet.path.read_bytes())
