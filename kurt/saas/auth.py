"""Password hashing and input validation for self-serve kurt/saas accounts.

Stdlib-only (hashlib.pbkdf2_hmac) — a one-way hash for password verification,
not encryption. This is deliberately a different primitive from
kurt/core/credential_transfer.py's Fernet-based export/import, which needs to
decrypt a backup file later; a login password only ever needs to be checked,
never recovered.
"""
import hashlib
import hmac
import os
import re

ITERATIONS = 600_000
_EMAIL_RE = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")


def valid_email(email):
    return isinstance(email, str) and 3 <= len(email) <= 254 and bool(_EMAIL_RE.fullmatch(email))


def valid_password(password):
    return isinstance(password, str) and 8 <= len(password) <= 256


def hash_password(password):
    salt = os.urandom(16)
    digest = hashlib.pbkdf2_hmac("sha256", password.encode(), salt, ITERATIONS)
    return f"{salt.hex()}${ITERATIONS}${digest.hex()}"


def verify_password(password, stored):
    try:
        salt_hex, iterations, digest_hex = stored.split("$")
        salt, iterations, expected = bytes.fromhex(salt_hex), int(iterations), bytes.fromhex(digest_hex)
    except (ValueError, AttributeError):
        return False
    actual = hashlib.pbkdf2_hmac("sha256", password.encode(), salt, iterations)
    return hmac.compare_digest(actual, expected)
