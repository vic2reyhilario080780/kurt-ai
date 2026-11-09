"""Server-owned subscription grants, hashed device tokens and atomic quotas.

SQLite is for a single control-plane host. No prompts, provider keys, datasets
or model responses are stored here. Billing providers must update grants through
an authenticated, verified integration; clients cannot change their own plan.
"""
from contextlib import contextmanager
import hashlib
from pathlib import Path
import secrets
import sqlite3
import time
import uuid


class Denied(Exception):
    def __init__(self, status, code):
        self.status, self.code = status, code
        super().__init__(code)


PLANS = {"starter": {"daily": 100, "minute": 10, "concurrent": 1},
         "pro": {"daily": 1000, "minute": 30, "concurrent": 2}}


class Store:
    def __init__(self, root):
        self.root = Path(root).resolve()
        self.root.mkdir(parents=True, exist_ok=True, mode=0o700)
        self.root.chmod(0o700)
        self.path = self.root / "control.db"
        if self.path.is_symlink():
            raise ValueError("State database cannot be a symlink")
        # Create privately before SQLite opens it, without a mode-0644 interval.
        import os
        fd = os.open(self.path, os.O_CREAT | os.O_RDWR | os.O_NOFOLLOW, 0o600)
        os.fchmod(fd, 0o600)
        os.close(fd)
        with self.db() as db:
            db.executescript('''
            CREATE TABLE IF NOT EXISTS tenants(id TEXT PRIMARY KEY, plan TEXT NOT NULL, active_until REAL NOT NULL);
            CREATE TABLE IF NOT EXISTS tokens(hash TEXT PRIMARY KEY, tenant TEXT NOT NULL, expires REAL NOT NULL, revoked INTEGER NOT NULL DEFAULT 0);
            CREATE TABLE IF NOT EXISTS counters(tenant TEXT, window TEXT, used INTEGER NOT NULL, PRIMARY KEY(tenant,window));
            CREATE TABLE IF NOT EXISTS leases(id TEXT PRIMARY KEY, tenant TEXT NOT NULL, expires REAL NOT NULL);
            CREATE TABLE IF NOT EXISTS audit(id TEXT PRIMARY KEY, tenant TEXT NOT NULL, action TEXT NOT NULL, status TEXT NOT NULL, created REAL NOT NULL);
            ''')

    @contextmanager
    def db(self):
        conn = sqlite3.connect(self.path, timeout=10, isolation_level=None)
        conn.row_factory = sqlite3.Row
        try:
            yield conn
        finally:
            conn.close()

    @staticmethod
    def digest(token):
        return hashlib.sha256(token.encode()).hexdigest()

    def grant(self, plan, days=30, tenant=None):
        if plan not in PLANS or type(days) is not int or not 1 <= days <= 366:
            raise ValueError("Invalid plan or subscription duration")
        tenant = str(uuid.UUID(tenant)) if tenant else str(uuid.uuid4())
        now = time.time()
        token = "kurt_live_" + secrets.token_urlsafe(32)
        expires = now + days * 86400
        with self.db() as db:
            db.execute("BEGIN IMMEDIATE")
            db.execute("INSERT INTO tenants VALUES(?,?,?) ON CONFLICT(id) DO UPDATE SET plan=excluded.plan,active_until=excluded.active_until", (tenant, plan, expires))
            db.execute("INSERT INTO tokens(hash,tenant,expires) VALUES(?,?,?)", (self.digest(token), tenant, expires))
            db.commit()
        return tenant, token

    def revoke(self, tenant):
        with self.db() as db:
            db.execute("UPDATE tokens SET revoked=1 WHERE tenant=?", (tenant,))

    def _identity(self, db, token):
        if not isinstance(token, str) or not 40 <= len(token) <= 100:
            raise Denied(401, "invalid_token")
        row = db.execute('''SELECT t.id,t.plan,t.active_until,k.expires,k.revoked FROM tokens k
                           JOIN tenants t ON t.id=k.tenant WHERE k.hash=?''', (self.digest(token),)).fetchone()
        if row is None or row["revoked"] or row["expires"] <= time.time():
            raise Denied(401, "invalid_token")
        return dict(row)

    def identity(self, token):
        with self.db() as db:
            row = self._identity(db, token)
        return {k: row[k] for k in ("id", "plan", "active_until")}

    def reserve(self, token, action):
        if action not in ("chat", "native"):
            raise Denied(403, "capability_not_allowed")
        now = time.time()
        lease = str(uuid.uuid4())
        with self.db() as db:
            db.execute("BEGIN IMMEDIATE")
            try:
                row = self._identity(db, token)
                if row["active_until"] <= now or row["plan"] not in PLANS:
                    raise Denied(403, "subscription_inactive")
                limits = PLANS[row["plan"]]
                db.execute("DELETE FROM leases WHERE expires<=?", (now,))
                db.execute("DELETE FROM counters WHERE window LIKE 'd:%' AND CAST(substr(window,3) AS INTEGER)<?", (int(now//86400)-2,))
                # Minute/day counters have separate prefixes; prune explicitly below.
                db.execute("DELETE FROM counters WHERE window LIKE 'm:%' AND CAST(substr(window,3) AS INTEGER)<?", (int(now//60)-2,))
                active = db.execute("SELECT COUNT(*) FROM leases WHERE tenant=?", (row["id"],)).fetchone()[0]
                total = db.execute("SELECT COUNT(*) FROM leases").fetchone()[0]
                if active >= limits["concurrent"] or total >= 16:
                    raise Denied(429, "concurrency_limit")
                windows = ((f"d:{int(now//86400)}", limits["daily"]), (f"m:{int(now//60)}", limits["minute"]))
                for window, maximum in windows:
                    count = db.execute("SELECT used FROM counters WHERE tenant=? AND window=?", (row["id"], window)).fetchone()
                    if count and count[0] >= maximum:
                        raise Denied(429, "quota_exceeded")
                for window, _ in windows:
                    db.execute("INSERT INTO counters VALUES(?,?,1) ON CONFLICT(tenant,window) DO UPDATE SET used=used+1", (row["id"], window))
                db.execute("INSERT INTO leases VALUES(?,?,?)", (lease, row["id"], now+300))
                db.execute("INSERT INTO audit VALUES(?,?,?,?,?)", (lease, row["id"], action, "started", now))
                db.commit()
            except Exception:
                db.rollback()
                raise
        return row["id"], lease

    def finish(self, tenant, lease, status):
        if status not in ("completed", "failed"):
            raise ValueError("Invalid audit status")
        with self.db() as db:
            db.execute("BEGIN IMMEDIATE")
            db.execute("DELETE FROM leases WHERE id=? AND tenant=?", (lease, tenant))
            db.execute("UPDATE audit SET status=? WHERE id=? AND tenant=?", (status, lease, tenant))
            db.commit()
