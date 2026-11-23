"""Apple App Store Server transaction verification.

Verifies a StoreKit 2 / App Store Server API signed transaction: a compact
JWS (JSON Web Signature) whose header carries an `x5c` certificate chain
(leaf, then intermediate) — see Apple's documented format at
https://developer.apple.com/documentation/appstoreserverapi/jwstransactiondecodedpayload

Trust anchor: Apple's own root CA certificate is deliberately NOT hardcoded
in this file. Reproducing a security-critical certificate's exact bytes from
memory risks an anchor that is subtly wrong in a way that wouldn't be
obviously wrong — either a safe-but-useless failure, or worse. Operators
must supply the real certificate (download it from
https://www.apple.com/certificateauthority/) via a file path, and
verify_transaction() takes the trusted root as an explicit parameter so
tests can substitute a synthetic one instead of Apple's real one.

What this does NOT do (documented gaps, not silent ones): full RFC 5280
path validation (policy constraints, name constraints, revocation/CRL/OCSP
checking). It does check each certificate's signature against its issuer's
public key and each certificate's validity period. Treat this as a
reasonable first pass, not a substitute for a dedicated PKI library review
before production use with real traffic.
"""
import base64
import json
from datetime import datetime, timezone

from cryptography import x509
from cryptography.exceptions import InvalidSignature
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.asymmetric import ec, padding, rsa
from cryptography.hazmat.primitives.asymmetric.utils import encode_dss_signature


class IAPVerificationError(Exception):
    pass


def _b64url_decode(segment):
    padding_needed = "=" * (-len(segment) % 4)
    return base64.urlsafe_b64decode(segment + padding_needed)


def _cert_currently_valid(cert):
    now = datetime.now(timezone.utc)
    return cert.not_valid_before_utc <= now <= cert.not_valid_after_utc


def _issued_by(cert, issuer_cert):
    issuer_key = issuer_cert.public_key()
    try:
        if isinstance(issuer_key, ec.EllipticCurvePublicKey):
            issuer_key.verify(cert.signature, cert.tbs_certificate_bytes, ec.ECDSA(cert.signature_hash_algorithm))
        elif isinstance(issuer_key, rsa.RSAPublicKey):
            issuer_key.verify(cert.signature, cert.tbs_certificate_bytes, padding.PKCS1v15(), cert.signature_hash_algorithm)
        else:
            return False
        return True
    except InvalidSignature:
        return False


def _verify_chain_to_root(leaf_and_intermediates, trusted_root):
    chain = [*leaf_and_intermediates, trusted_root]
    for cert in chain:
        if not _cert_currently_valid(cert):
            return False
    for i in range(len(chain) - 1):
        if not _issued_by(chain[i], chain[i + 1]):
            return False
    return True


def verify_transaction(signed_payload, *, trusted_root_der):
    """Verify an Apple-signed JWS and return its decoded payload dict.

    trusted_root_der: DER bytes of the certificate the chain must terminate
    at (Apple's real root in production; a synthetic test root in tests).
    Raises IAPVerificationError on any failure — never returns a payload
    for a transaction that didn't verify.
    """
    try:
        header_b64, payload_b64, signature_b64 = signed_payload.split(".")
    except (ValueError, AttributeError) as exc:
        raise IAPVerificationError("malformed_jws") from exc

    try:
        header = json.loads(_b64url_decode(header_b64))
        payload = json.loads(_b64url_decode(payload_b64))
        signature = _b64url_decode(signature_b64)
    except (ValueError, UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise IAPVerificationError("malformed_jws") from exc

    if header.get("alg") != "ES256":
        raise IAPVerificationError("unsupported_algorithm")

    chain_b64 = header.get("x5c")
    if not chain_b64 or not isinstance(chain_b64, list) or not 1 <= len(chain_b64) <= 5:
        raise IAPVerificationError("missing_certificate_chain")

    try:
        certs = [x509.load_der_x509_certificate(base64.b64decode(c)) for c in chain_b64]
        trusted_root = x509.load_der_x509_certificate(trusted_root_der)
    except (ValueError, TypeError) as exc:
        raise IAPVerificationError("invalid_certificate") from exc

    if not _verify_chain_to_root(certs, trusted_root):
        raise IAPVerificationError("untrusted_certificate_chain")

    if len(signature) != 64:
        raise IAPVerificationError("invalid_signature")
    r = int.from_bytes(signature[:32], "big")
    s = int.from_bytes(signature[32:], "big")

    leaf_public_key = certs[0].public_key()
    if not isinstance(leaf_public_key, ec.EllipticCurvePublicKey):
        raise IAPVerificationError("unsupported_key_type")
    try:
        leaf_public_key.verify(
            encode_dss_signature(r, s),
            f"{header_b64}.{payload_b64}".encode(),
            ec.ECDSA(hashes.SHA256()),
        )
    except InvalidSignature as exc:
        raise IAPVerificationError("invalid_signature") from exc

    return payload
