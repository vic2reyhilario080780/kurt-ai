"""IAP receipt/purchase verification — synthetic credentials and signed
payloads only. No real Apple/Google/Huawei traffic or production certs."""
import base64
import datetime
import json
import tempfile
import time
import unittest

import httpx

from cryptography import x509
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import ec, rsa
from cryptography.hazmat.primitives.asymmetric.utils import decode_dss_signature
from cryptography.x509.oid import NameOID

from kurt.saas import iap, iap_apple, iap_google, iap_huawei
from kurt.saas.app import App
from kurt.saas.store import Store


def _b64url(data: bytes) -> str:
    return base64.urlsafe_b64encode(data).rstrip(b"=").decode()


def _make_cert(subject, issuer, public_key, signing_key, is_ca):
    now = datetime.datetime.now(datetime.timezone.utc)
    return (
        x509.CertificateBuilder()
        .subject_name(x509.Name([x509.NameAttribute(NameOID.COMMON_NAME, subject)]))
        .issuer_name(x509.Name([x509.NameAttribute(NameOID.COMMON_NAME, issuer)]))
        .public_key(public_key)
        .serial_number(x509.random_serial_number())
        .not_valid_before(now - datetime.timedelta(days=1))
        .not_valid_after(now + datetime.timedelta(days=365))
        .add_extension(x509.BasicConstraints(ca=is_ca, path_length=None), critical=True)
        .sign(signing_key, hashes.SHA256())
    )


def _der(cert):
    return cert.public_bytes(encoding=serialization.Encoding.DER)


def make_apple_chain():
    """A synthetic root -> intermediate -> leaf chain, standing in for
    Apple's real one — see iap_apple.py's module docstring for why the real
    certificate is never embedded in this codebase."""
    root_key = ec.generate_private_key(ec.SECP256R1())
    root_cert = _make_cert("Test Root", "Test Root", root_key.public_key(), root_key, True)
    inter_key = ec.generate_private_key(ec.SECP256R1())
    inter_cert = _make_cert("Test Intermediate", "Test Root", inter_key.public_key(), root_key, True)
    leaf_key = ec.generate_private_key(ec.SECP256R1())
    leaf_cert = _make_cert("Test Leaf", "Test Intermediate", leaf_key.public_key(), inter_key, False)
    return root_cert, inter_cert, leaf_key, leaf_cert


def sign_apple_jws(leaf_key, leaf_cert, inter_cert, payload):
    header = {"alg": "ES256", "x5c": [
        base64.b64encode(_der(leaf_cert)).decode(),
        base64.b64encode(_der(inter_cert)).decode(),
    ]}
    header_b64 = _b64url(json.dumps(header).encode())
    payload_b64 = _b64url(json.dumps(payload).encode())
    signing_input = f"{header_b64}.{payload_b64}".encode()
    der_sig = leaf_key.sign(signing_input, ec.ECDSA(hashes.SHA256()))
    r, s = decode_dss_signature(der_sig)
    raw_sig = r.to_bytes(32, "big") + s.to_bytes(32, "big")
    return f"{header_b64}.{payload_b64}.{_b64url(raw_sig)}"


class AppleIAPTests(unittest.TestCase):
    def setUp(self):
        self.root_cert, self.inter_cert, self.leaf_key, self.leaf_cert = make_apple_chain()
        self.root_der = _der(self.root_cert)
        self.payload = {"transactionId": "1000000123", "productId": "kurt_pro_monthly", "bundleId": "com.kurtmobile"}

    def test_valid_transaction_verifies(self):
        jws = sign_apple_jws(self.leaf_key, self.leaf_cert, self.inter_cert, self.payload)
        result = iap_apple.verify_transaction(jws, trusted_root_der=self.root_der)
        self.assertEqual(result["productId"], "kurt_pro_monthly")

    def test_tampered_payload_rejected(self):
        jws = sign_apple_jws(self.leaf_key, self.leaf_cert, self.inter_cert, self.payload)
        header_b64, payload_b64, sig_b64 = jws.split(".")
        tampered_payload = _b64url(json.dumps({**self.payload, "productId": "kurt_pro_yearly"}).encode())
        tampered = f"{header_b64}.{tampered_payload}.{sig_b64}"
        with self.assertRaises(iap_apple.IAPVerificationError):
            iap_apple.verify_transaction(tampered, trusted_root_der=self.root_der)

    def test_untrusted_root_rejected(self):
        jws = sign_apple_jws(self.leaf_key, self.leaf_cert, self.inter_cert, self.payload)
        other_root_key = ec.generate_private_key(ec.SECP256R1())
        other_root = _make_cert("Other Root", "Other Root", other_root_key.public_key(), other_root_key, True)
        with self.assertRaises(iap_apple.IAPVerificationError):
            iap_apple.verify_transaction(jws, trusted_root_der=_der(other_root))

    def test_malformed_jws_rejected(self):
        with self.assertRaises(iap_apple.IAPVerificationError):
            iap_apple.verify_transaction("not-a-jws", trusted_root_der=self.root_der)

    def test_wrong_algorithm_rejected(self):
        header_b64 = _b64url(json.dumps({"alg": "RS256", "x5c": []}).encode())
        payload_b64 = _b64url(json.dumps(self.payload).encode())
        with self.assertRaises(iap_apple.IAPVerificationError):
            iap_apple.verify_transaction(f"{header_b64}.{payload_b64}.{_b64url(b'x')}", trusted_root_der=self.root_der)


def make_google_service_account():
    key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    pem = key.private_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PrivateFormat.PKCS8,
        encryption_algorithm=serialization.NoEncryption(),
    ).decode()
    return {"client_email": "test@test.iam.gserviceaccount.com", "private_key": pem,
            "token_uri": "https://oauth2.googleapis.com/token"}


class GoogleIAPTests(unittest.IsolatedAsyncioTestCase):
    def setUp(self):
        self.service_account = make_google_service_account()

    async def test_active_subscription_verifies_and_returns_line_item(self):
        def handler(request):
            if "oauth2.googleapis.com" in str(request.url):
                return httpx.Response(200, json={"access_token": "fake-token"})
            self.assertEqual(request.headers["authorization"], "Bearer fake-token")
            return httpx.Response(200, json={
                "subscriptionState": "SUBSCRIPTION_STATE_ACTIVE",
                "lineItems": [{"productId": "kurt_pro_monthly", "expiryTime": "2027-01-01T00:00:00Z"}],
            })
        async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as client:
            result = await iap_google.verify_purchase(
                service_account=self.service_account, package_name="com.kurtmobile",
                product_id="kurt_pro_monthly", purchase_token="tok", client=client)
        self.assertEqual(result["productId"], "kurt_pro_monthly")

    async def test_inactive_subscription_rejected(self):
        def handler(request):
            if "oauth2.googleapis.com" in str(request.url):
                return httpx.Response(200, json={"access_token": "x"})
            return httpx.Response(200, json={"subscriptionState": "SUBSCRIPTION_STATE_CANCELED", "lineItems": []})
        async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as client:
            with self.assertRaises(iap_google.IAPVerificationError):
                await iap_google.verify_purchase(
                    service_account=self.service_account, package_name="com.kurtmobile",
                    product_id="kurt_pro_monthly", purchase_token="tok", client=client)

    async def test_wrong_product_id_rejected(self):
        def handler(request):
            if "oauth2.googleapis.com" in str(request.url):
                return httpx.Response(200, json={"access_token": "x"})
            return httpx.Response(200, json={
                "subscriptionState": "SUBSCRIPTION_STATE_ACTIVE",
                "lineItems": [{"productId": "some_other_product"}],
            })
        async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as client:
            with self.assertRaises(iap_google.IAPVerificationError):
                await iap_google.verify_purchase(
                    service_account=self.service_account, package_name="com.kurtmobile",
                    product_id="kurt_pro_monthly", purchase_token="tok", client=client)

    async def test_token_exchange_failure_raises(self):
        def handler(request):
            return httpx.Response(401, json={"error": "invalid_grant"})
        async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as client:
            with self.assertRaises(iap_google.IAPVerificationError):
                await iap_google.verify_purchase(
                    service_account=self.service_account, package_name="com.kurtmobile",
                    product_id="kurt_pro_monthly", purchase_token="tok", client=client)


class HuaweiIAPTests(unittest.IsolatedAsyncioTestCase):
    async def test_active_purchase_verifies(self):
        def handler(request):
            if "oauth-login.cloud.huawei.com" in str(request.url):
                return httpx.Response(200, json={"access_token": "fake-token"})
            return httpx.Response(200, json={
                "responseCode": "0",
                "purchaseTokenData": json.dumps({"productId": "kurt_pro_monthly", "purchaseState": 0}),
            })
        async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as client:
            result = await iap_huawei.verify_purchase(
                client_id="id", client_secret="secret", product_id="kurt_pro_monthly",
                purchase_token="tok", client=client)
        self.assertEqual(result["productId"], "kurt_pro_monthly")

    async def test_cancelled_purchase_rejected(self):
        def handler(request):
            if "oauth-login.cloud.huawei.com" in str(request.url):
                return httpx.Response(200, json={"access_token": "x"})
            return httpx.Response(200, json={
                "responseCode": "0",
                "purchaseTokenData": json.dumps({"productId": "kurt_pro_monthly", "purchaseState": 1}),
            })
        async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as client:
            with self.assertRaises(iap_huawei.IAPVerificationError):
                await iap_huawei.verify_purchase(
                    client_id="id", client_secret="secret", product_id="kurt_pro_monthly",
                    purchase_token="tok", client=client)

    async def test_error_response_code_rejected(self):
        def handler(request):
            if "oauth-login.cloud.huawei.com" in str(request.url):
                return httpx.Response(200, json={"access_token": "x"})
            return httpx.Response(200, json={"responseCode": "20001"})
        async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as client:
            with self.assertRaises(iap_huawei.IAPVerificationError):
                await iap_huawei.verify_purchase(
                    client_id="id", client_secret="secret", product_id="kurt_pro_monthly",
                    purchase_token="tok", client=client)


class PlanMappingTests(unittest.TestCase):
    def test_known_product_maps_to_plan(self):
        self.assertEqual(iap.plan_for_product("kurt_pro_monthly"), ("pro", 31))

    def test_unknown_product_rejected(self):
        with self.assertRaises(iap.IAPVerificationError):
            iap.plan_for_product("not_a_real_product")


class IAPRouteTests(unittest.IsolatedAsyncioTestCase):
    """End-to-end through the real ASGI App, exercising the /v1/iap/apple
    route specifically (no network needed — pure local JWS verification),
    confirming it actually calls Store.grant() and extends the tenant's plan."""

    async def asyncSetUp(self):
        self.tmp = tempfile.TemporaryDirectory(); self.addCleanup(self.tmp.cleanup)
        self.store = Store(self.tmp.name)
        self.tenant, self.token = self.store.grant('starter', days=5)
        self.root_cert, self.inter_cert, self.leaf_key, self.leaf_cert = make_apple_chain()
        self.app = App(self.store, iap_config={"apple": {"trusted_root_der": _der(self.root_cert)}})
        self.client = httpx.AsyncClient(transport=httpx.ASGITransport(app=self.app), base_url='https://test')
        self.addAsyncCleanup(self.client.aclose)

    def auth(self):
        return {'Authorization': 'Bearer ' + self.token}

    async def test_verified_purchase_grants_plan(self):
        jws = sign_apple_jws(self.leaf_key, self.leaf_cert, self.inter_cert,
                              {"transactionId": "1", "productId": "kurt_pro_yearly", "bundleId": "com.kurtmobile"})
        response = await self.client.post('/v1/iap/apple', headers=self.auth(), json={'signedTransaction': jws})
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()['tenant']['plan'], 'pro')
        self.assertGreater(response.json()['tenant']['active_until'], time.time() + 300 * 86400)

    async def test_tampered_transaction_rejected_and_plan_unchanged(self):
        # Swap in a different (still well-formed) payload under the original
        # signature — flipping a single base64 character isn't reliably a
        # byte-level change (trailing bits in an unpadded base64 group can
        # be redundant), but substituting the whole payload always changes
        # the signed bytes in a way the original signature can't match.
        jws = sign_apple_jws(self.leaf_key, self.leaf_cert, self.inter_cert,
                              {"transactionId": "1", "productId": "kurt_pro_yearly", "bundleId": "com.kurtmobile"})
        header_b64, _, sig_b64 = jws.split(".")
        forged_payload_b64 = _b64url(json.dumps(
            {"transactionId": "1", "productId": "kurt_pro_monthly", "bundleId": "com.kurtmobile"}).encode())
        tampered = f"{header_b64}.{forged_payload_b64}.{sig_b64}"
        response = await self.client.post('/v1/iap/apple', headers=self.auth(), json={'signedTransaction': tampered})
        self.assertEqual(response.status_code, 402)
        self.assertEqual(self.store.identity(self.token)['plan'], 'starter')

    async def test_unknown_product_rejected(self):
        jws = sign_apple_jws(self.leaf_key, self.leaf_cert, self.inter_cert,
                              {"transactionId": "1", "productId": "not_a_real_product", "bundleId": "com.kurtmobile"})
        response = await self.client.post('/v1/iap/apple', headers=self.auth(), json={'signedTransaction': jws})
        self.assertEqual(response.status_code, 402)

    async def test_unconfigured_provider_returns_503(self):
        response = await self.client.post('/v1/iap/google', headers=self.auth(), json={'productId': 'x', 'purchaseToken': 'y'})
        self.assertEqual(response.status_code, 503)

    async def test_unknown_provider_404(self):
        response = await self.client.post('/v1/iap/not-a-store', headers=self.auth(), json={})
        self.assertEqual(response.status_code, 404)

    async def test_requires_authentication(self):
        response = await self.client.post('/v1/iap/apple', json={'signedTransaction': 'x'})
        self.assertEqual(response.status_code, 401)

    async def test_extra_fields_rejected(self):
        jws = sign_apple_jws(self.leaf_key, self.leaf_cert, self.inter_cert,
                              {"transactionId": "1", "productId": "kurt_pro_yearly", "bundleId": "com.kurtmobile"})
        response = await self.client.post('/v1/iap/apple', headers=self.auth(),
                                           json={'signedTransaction': jws, 'tenant': 'someone-elses-id'})
        self.assertEqual(response.status_code, 402)


if __name__ == '__main__':
    unittest.main()
