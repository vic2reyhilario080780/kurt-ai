"""Google Play Developer API purchase verification.

Unlike Apple's locally-verifiable signed transaction (see iap_apple.py),
there is no client-held cryptographic receipt to check here. Google Play's
model is: authenticate as a service account (OAuth2 JWT-bearer grant, RFC
7523), then ask Google's own API for the purchase's current state. Trust
comes from the HTTPS + OAuth2-authenticated API response itself, not from
verifying a signature client-side.

Needs a Google Cloud service account with Android Publisher API access,
downloaded as JSON and supplied via KURT_SAAS_GOOGLE_SERVICE_ACCOUNT_PATH —
not fabricated or embedded here.
"""
import base64
import json
import time

import httpx
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import padding

SCOPE = "https://www.googleapis.com/auth/androidpublisher"
DEFAULT_TOKEN_URI = "https://oauth2.googleapis.com/token"
ACTIVE_STATES = {"SUBSCRIPTION_STATE_ACTIVE", "SUBSCRIPTION_STATE_IN_GRACE_PERIOD"}


class IAPVerificationError(Exception):
    pass


def _b64url(data: bytes) -> str:
    return base64.urlsafe_b64encode(data).rstrip(b"=").decode()


def _service_account_jwt(service_account, scope, audience):
    now = int(time.time())
    header = {"alg": "RS256", "typ": "JWT"}
    claims = {
        "iss": service_account["client_email"],
        "scope": scope,
        "aud": audience,
        "iat": now,
        "exp": now + 3600,
    }
    signing_input = f"{_b64url(json.dumps(header).encode())}.{_b64url(json.dumps(claims).encode())}"
    try:
        private_key = serialization.load_pem_private_key(service_account["private_key"].encode(), password=None)
    except (KeyError, ValueError) as exc:
        raise IAPVerificationError("invalid_service_account") from exc
    signature = private_key.sign(signing_input.encode(), padding.PKCS1v15(), hashes.SHA256())
    return f"{signing_input}.{_b64url(signature)}"


async def _access_token(service_account, token_uri, client):
    assertion = _service_account_jwt(service_account, SCOPE, token_uri)
    try:
        response = await client.post(
            token_uri,
            data={"grant_type": "urn:ietf:params:oauth:grant-type:jwt-bearer", "assertion": assertion},
            timeout=20,
        )
        response.raise_for_status()
    except httpx.HTTPError as exc:
        raise IAPVerificationError("token_exchange_failed") from exc
    token = response.json().get("access_token")
    if not isinstance(token, str):
        raise IAPVerificationError("token_exchange_failed")
    return token


async def verify_purchase(*, service_account, package_name, product_id, purchase_token, client=None):
    """Verify a Google Play subscription purchase token against Google's own
    API. Returns the matching line-item dict. Raises IAPVerificationError if
    the subscription can't be confirmed active for that product."""
    owns_client = client is None
    client = client or httpx.AsyncClient()
    try:
        token_uri = service_account.get("token_uri", DEFAULT_TOKEN_URI)
        access_token = await _access_token(service_account, token_uri, client)
        url = (
            "https://androidpublisher.googleapis.com/androidpublisher/v3/applications/"
            f"{package_name}/purchases/subscriptionsv2/tokens/{purchase_token}"
        )
        try:
            response = await client.get(url, headers={"Authorization": f"Bearer {access_token}"}, timeout=20)
            response.raise_for_status()
        except httpx.HTTPError as exc:
            raise IAPVerificationError("purchase_lookup_failed") from exc
        data = response.json()
    finally:
        if owns_client:
            await client.aclose()

    if data.get("subscriptionState") not in ACTIVE_STATES:
        raise IAPVerificationError("subscription_not_active")
    for item in data.get("lineItems", []):
        if item.get("productId") == product_id:
            return item
    raise IAPVerificationError("product_not_in_purchase")
