"""Integer pico-USD, atomic holds and append-only monetary entries. No prompts/keys."""
from contextlib import contextmanager
from decimal import Decimal, InvalidOperation
import hashlib
import json
import secrets
import time
import uuid

from kurt.saas.store import Store, Denied
from . import WalletError

SCALE = 10**12
MAX_MONEY = 10**18  # $1M, safely below SQLite signed-int limit.
ACTIVE = ('reserved', 'submitted', 'pending')


def units(value):
    if isinstance(value, (bool, float)): raise ValueError('Money must be a decimal string, never a float.')
    try:
        decimal = Decimal(value)
        scaled = decimal * SCALE
        if not decimal.is_finite() or decimal < 0 or scaled != scaled.to_integral_value() or scaled > MAX_MONEY:
            raise ValueError('Invalid or excessively precise USD amount.')
        return int(scaled)
    except (InvalidOperation, TypeError, OverflowError):
        raise ValueError('Invalid USD amount.') from None


def usd(value):
    return format(Decimal(value)/SCALE, 'f')


def safe_id(value):
    if not isinstance(value, str) or not 1 <= len(value) <= 200 or any(ord(c) < 32 for c in value):
        raise ValueError('Invalid reference.')
    return value


class Wallet(Store):
    def __init__(self, root):
        super().__init__(root)
        with self.db() as db:
            db.executescript('''
            CREATE TABLE IF NOT EXISTS wallet_accounts(tenant TEXT PRIMARY KEY, balance INTEGER NOT NULL DEFAULT 0);
            CREATE TABLE IF NOT EXISTS wallet_entries(id TEXT PRIMARY KEY, tenant TEXT NOT NULL, delta INTEGER NOT NULL,
                reference TEXT NOT NULL UNIQUE, kind TEXT NOT NULL, created REAL NOT NULL, note TEXT NOT NULL DEFAULT '');
            CREATE TABLE IF NOT EXISTS wallet_requests(id TEXT PRIMARY KEY, tenant TEXT NOT NULL, scope TEXT NOT NULL,
                dedupe TEXT NOT NULL, fingerprint TEXT NOT NULL, provider TEXT NOT NULL, model TEXT NOT NULL,
                status TEXT NOT NULL, hold INTEGER NOT NULL, cost INTEGER, usage TEXT NOT NULL DEFAULT '{}',
                provider_id TEXT, http_status INTEGER, basis TEXT, evidence TEXT, created REAL NOT NULL,
                UNIQUE(tenant,scope,dedupe));
            CREATE UNIQUE INDEX IF NOT EXISTS wallet_billed_provider_id ON wallet_requests(provider,provider_id)
                WHERE provider_id IS NOT NULL;
            CREATE TABLE IF NOT EXISTS wallet_sessions(hash TEXT PRIMARY KEY, tenant TEXT NOT NULL, provider TEXT NOT NULL,
                cli TEXT NOT NULL, expires REAL NOT NULL, budget INTEGER NOT NULL, parent TEXT NOT NULL);
            CREATE TABLE IF NOT EXISTS wallet_resources(provider TEXT, resource TEXT, tenant TEXT, request_id TEXT,
                PRIMARY KEY(provider,resource));
            CREATE TABLE IF NOT EXISTS wallet_topups(id TEXT PRIMARY KEY, tenant TEXT NOT NULL, cents INTEGER NOT NULL,
                session TEXT UNIQUE, intent TEXT UNIQUE, state TEXT NOT NULL, refunded INTEGER NOT NULL DEFAULT 0,
                disputed INTEGER NOT NULL DEFAULT 0, dispute_id TEXT, applied_reversal INTEGER NOT NULL DEFAULT 0);
            CREATE TABLE IF NOT EXISTS wallet_payment_events(id TEXT PRIMARY KEY, digest TEXT NOT NULL, created REAL NOT NULL);
            ''')

    @contextmanager
    def transaction(self):
        with self.db() as db:
            db.execute('BEGIN IMMEDIATE')
            try:
                yield db
                db.commit()
            except BaseException:
                db.rollback(); raise

    def _account(self, db, tenant):
        if not db.execute('SELECT 1 FROM tenants WHERE id=?', (tenant,)).fetchone():
            raise WalletError('unknown_account', 404)
        db.execute('INSERT OR IGNORE INTO wallet_accounts(tenant) VALUES(?)', (tenant,))

    def _entry(self, db, tenant, delta, reference, kind, note=""):
        self._account(db, tenant)
        previous = db.execute('SELECT * FROM wallet_entries WHERE reference=?', (reference,)).fetchone()
        if previous:
            if previous['tenant'] != tenant or previous['delta'] != delta or previous['kind'] != kind:
                raise WalletError('idempotency_conflict')
            return False
        balance = db.execute('SELECT balance FROM wallet_accounts WHERE tenant=?', (tenant,)).fetchone()[0]
        if abs(balance+delta) > MAX_MONEY: raise WalletError('balance_limit')
        db.execute('INSERT INTO wallet_entries VALUES(?,?,?,?,?,?,?)', (str(uuid.uuid4()), tenant, delta, reference, kind, time.time(), note))
        db.execute('UPDATE wallet_accounts SET balance=balance+? WHERE tenant=?', (delta, tenant))
        return True

    def manual_credit(self, tenant, amount, reference, reason):
        value = units(amount)
        if not value: raise ValueError('Credit must be positive.')
        # An operator credit is explicitly not a verified card purchase.
        safe_id(reference); safe_id(reason)
        with self.transaction() as db:
            return self._entry(db, tenant, value, 'manual:'+reference, 'manual_credit', reason)

    def auth(self, token):
        if not isinstance(token, str) or not 40<=len(token)<=100: raise WalletError('invalid_token', 401)
        if token.startswith('kurt_cli_'):
            with self.db() as db:
                row = db.execute('SELECT * FROM wallet_sessions WHERE hash=?', (self.digest(token),)).fetchone()
                if not row or row['expires'] <= time.time(): raise WalletError('expired_session', 401)
                active = db.execute('SELECT active_until FROM tenants WHERE id=?', (row['tenant'],)).fetchone()
                # Revoking owner tokens also invalidates their child sessions.
                valid = db.execute('SELECT 1 FROM tokens WHERE hash=? AND tenant=? AND revoked=0 AND expires>?', (row['parent'], row['tenant'], time.time())).fetchone()
                if not active or active[0] <= time.time() or not valid: raise WalletError('inactive_account', 403)
            return {'tenant': row['tenant'], 'scope': self.digest(token), 'provider': row['provider'], 'cli': row['cli']}
        try: identity = self.identity(token)
        except Denied as exc: raise WalletError(exc.code, exc.status) from None
        if identity['active_until'] <= time.time(): raise WalletError('inactive_account', 403)
        return {'tenant': identity['id'], 'scope': 'owner', 'provider': None, 'cli': None}

    def session(self, owner_token, provider, cli, budget='5', ttl=300):
        identity = self.auth(owner_token)
        if identity['scope'] != 'owner': raise WalletError('owner_token_required', 403)
        value = units(budget)
        if value <= 0 or type(ttl) is not int or not 30 <= ttl <= 600: raise ValueError('Invalid session bounds.')
        token = 'kurt_cli_'+secrets.token_urlsafe(32)
        with self.transaction() as db:
            self._account(db, identity['tenant'])
            db.execute('INSERT INTO wallet_sessions VALUES(?,?,?,?,?,?,?)',
                (self.digest(token), identity['tenant'], provider, cli, time.time()+ttl, value, self.digest(owner_token)))
        return token

    def _available(self, db, tenant):
        self._account(db, tenant)
        balance = db.execute('SELECT balance FROM wallet_accounts WHERE tenant=?', (tenant,)).fetchone()[0]
        held = db.execute("SELECT COALESCE(SUM(hold),0) FROM wallet_requests WHERE tenant=? AND status IN ('reserved','submitted','pending')", (tenant,)).fetchone()[0]
        return balance, held

    def summary(self, tenant):
        with self.transaction() as db:
            balance, held = self._available(db, tenant)
        return {'currency': 'USD', 'markup_percent': 0, 'balance_usd': usd(balance),
                'reserved_usd': usd(held), 'available_usd': usd(balance-held)}

    def history(self, tenant, limit=50):
        if type(limit) is not int or not 1 <= limit <= 100: raise ValueError('Invalid limit.')
        with self.db() as db:
            rows = db.execute('SELECT id,delta,reference,kind,created,note FROM wallet_entries WHERE tenant=? ORDER BY created DESC LIMIT ?', (tenant, limit)).fetchall()
            calls = db.execute('SELECT * FROM wallet_requests WHERE tenant=? ORDER BY created DESC LIMIT ?', (tenant, limit)).fetchall()
        return {'entries': [{**dict(r), 'delta_usd': usd(r['delta'])} for r in rows],
                'requests': [{k: r[k] for k in ('id','provider','model','status','provider_id','basis','evidence','created')}
                    | {'reserved_usd': usd(r['hold']), 'cost_usd': None if r['cost'] is None else usd(r['cost']), 'usage': json.loads(r['usage'])} for r in calls]}

    def reserve_money(self, identity, provider, model, hold, dedupe, fingerprint):
        value = units(hold)
        if value <= 0: raise ValueError('A positive reservation is required.')
        safe_id(dedupe); safe_id(provider); safe_id(model)
        tenant, scope = identity['tenant'], identity['scope']
        if identity['provider'] and identity['provider'] != provider: raise WalletError('session_provider_mismatch', 403)
        with self.transaction() as db:
            old = db.execute('SELECT * FROM wallet_requests WHERE tenant=? AND scope=? AND dedupe=?', (tenant, scope, dedupe)).fetchone()
            if old:
                raise WalletError('duplicate_request_not_replayed' if old['fingerprint'] == fingerprint else 'idempotency_conflict')
            balance, held = self._available(db, tenant)
            if balance-held < value: raise WalletError('insufficient_wallet_balance', 402)
            if scope != 'owner':
                session = db.execute('SELECT budget,expires FROM wallet_sessions WHERE hash=?', (scope,)).fetchone()
                if not session or session['expires'] <= time.time(): raise WalletError('expired_session', 401)
                used = db.execute("SELECT COALESCE(SUM(CASE WHEN status IN ('reserved','submitted','pending') THEN hold ELSE COALESCE(cost,0) END),0) FROM wallet_requests WHERE scope=?", (scope,)).fetchone()[0]
                if used+value > session['budget']: raise WalletError('session_budget_exhausted', 402)
            active = db.execute("SELECT COUNT(*) FROM wallet_requests WHERE tenant=? AND status IN ('reserved','submitted')", (tenant,)).fetchone()[0]
            if active >= 4: raise WalletError('concurrency_limit', 429)
            if db.execute('SELECT COUNT(*) FROM wallet_requests WHERE tenant=? AND created>?', (tenant, time.time()-60)).fetchone()[0] >= 60:
                raise WalletError('request_rate_limit', 429)
            request = str(uuid.uuid4())
            db.execute('INSERT INTO wallet_requests(id,tenant,scope,dedupe,fingerprint,provider,model,status,hold,created) VALUES(?,?,?,?,?,?,?,?,?,?)',
                (request,tenant,scope,dedupe,fingerprint,provider,model,'reserved',value,time.time()))
        return request

    def request(self, tenant, request):
        with self.db() as db: row = db.execute('SELECT * FROM wallet_requests WHERE id=? AND tenant=?', (request,tenant)).fetchone()
        if not row: raise WalletError('request_not_found', 404)
        return dict(row)

    def submitted(self, tenant, request):
        with self.transaction() as db:
            db.execute("UPDATE wallet_requests SET status='submitted' WHERE id=? AND tenant=? AND status='reserved'", (request,tenant))

    def record(self, tenant, request, *, provider_id=None, usage=None, http_status=None, pending=True):
        # Only gateway-derived numeric usage fields, never complete provider bodies.
        clean = {}
        for key, value in (usage or {}).items():
            if key in {'input_tokens','output_tokens','cached_tokens','cache_write_tokens','audio_seconds','images','video_seconds','compute_seconds'}:
                if isinstance(value, bool) or not isinstance(value, (int,str)) or len(str(value)) > 40: continue
                try:
                    if Decimal(value).is_finite() and Decimal(value) >= 0: clean[key] = value
                except InvalidOperation: pass
        if provider_id is not None: safe_id(provider_id)
        with self.transaction() as db:
            row = db.execute('SELECT * FROM wallet_requests WHERE id=? AND tenant=?', (request,tenant)).fetchone()
            if not row: raise WalletError('request_not_found',404)
            if row['status'] in ('settled','void'): return
            clean={**json.loads(row['usage']),**clean}
            db.execute("UPDATE wallet_requests SET status=?,provider_id=COALESCE(?,provider_id),usage=?,http_status=? WHERE id=?",
                       ('pending' if pending else row['status'],provider_id,json.dumps(clean),http_status,request))

    def settle(self, tenant, request, amount, *, basis, evidence):
        value = units(amount); safe_id(basis); safe_id(evidence)
        with self.transaction() as db:
            row = db.execute('SELECT * FROM wallet_requests WHERE id=? AND tenant=?', (request,tenant)).fetchone()
            if not row: raise WalletError('request_not_found',404)
            if row['status'] in ('settled','void'):
                if row['cost'] != value or row['evidence'] != evidence: raise WalletError('settlement_conflict')
                return False
            self._entry(db,tenant,-value,'usage:'+request,'provider_cost')
            # Actual confirmed cost can exceed an estimated hold. Record the real
            # amount, including debt, rather than hide it or invent a price cap.
            db.execute("UPDATE wallet_requests SET status='settled',cost=?,basis=?,evidence=? WHERE id=?", (value,basis,evidence,request))
        return True

    def correct(self,tenant,request,amount,*,evidence):
        """Operator-only correction: append a delta, never rewrite ledger history."""
        value=units(amount);safe_id(evidence)
        reference='correction:'+request+':'+hashlib.sha256(evidence.encode()).hexdigest()
        with self.transaction() as db:
            row=db.execute('SELECT * FROM wallet_requests WHERE id=? AND tenant=?',(request,tenant)).fetchone()
            if not row or row['status']!='settled': raise WalletError('settled_request_required')
            previous=db.execute('SELECT 1 FROM wallet_entries WHERE reference=?',(reference,)).fetchone()
            if previous:
                if row['cost']==value:return False
                raise WalletError('stale_correction_or_evidence_conflict')
            self._entry(db,tenant,row['cost']-value,reference,'provider_cost_adjustment',evidence)
            db.execute('UPDATE wallet_requests SET cost=?,basis=?,evidence=? WHERE id=?',
                       (value,'operator_verified_provider_bill',evidence,request))
        return True

    def pending(self, tenant, request):
        with self.transaction() as db:
            db.execute("UPDATE wallet_requests SET status='pending' WHERE id=? AND tenant=? AND status IN ('reserved','submitted')", (request,tenant))

    def resource(self, tenant, provider, resource):
        if provider == 'replicate-version': resource=tenant+':'+resource
        with self.db() as db: row = db.execute('SELECT * FROM wallet_resources WHERE provider=? AND resource=? AND tenant=?', (provider,resource,tenant)).fetchone()
        if not row: raise WalletError('resource_not_found',404)
        return dict(row)

    def add_resource(self, tenant, provider, resource, request):
        if provider == 'replicate-version': resource=tenant+':'+resource
        safe_id(resource)
        with self.transaction() as db:
            row = db.execute('SELECT * FROM wallet_resources WHERE provider=? AND resource=?', (provider,resource)).fetchone()
            if row and (row['tenant'] != tenant or row['request_id'] != request): raise WalletError('resource_conflict')
            db.execute('INSERT OR IGNORE INTO wallet_resources VALUES(?,?,?,?)', (provider,resource,tenant,request))
