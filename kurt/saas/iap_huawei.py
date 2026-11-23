"""Huawei AppGallery Connect in-app purchase verification.

LOWER CONFIDENCE than iap_apple.py/iap_google.py: Huawei's IAP API surface
is far less commonly documented than Apple's or Google's, and the exact
endpoint path/field names below should be cross-checked against Huawei's
current official docs before relying on this against real traffic:
https://developer.huawei.com/consumer/en/doc/development/HMSCore-Guides/open-platform-verifying-purchase-0000001050033439

The overall shape — OAuth2 client-credentials grant, then an authenticated
server-to-server call that returns the purchase's current state — mirrors
iap_google.py and is standard regardless of the exact field names; only that
has been verified here (with synthetic HTTP responses, not a real Huawei
sandbox).
"""
import json

import httpx

TOKEN_URL = "https://oauth-login.cloud.huawei.com/oauth2/v3/token"
VERIFY_URL = "https://orders-dre.iap.hicloud.com/applications/purchases/tokens/verify"


class IAPVerificationError(Exception):
    pass


async def _access_token(client_id, client_secret, client):
    try:
        response = await client.post(
            TOKEN_URL,
            data={"grant_type": "client_credentials", "client_id": client_id, "client_secret": client_secret},
            timeout=20,
        )
        response.raise_for_status()
    except httpx.HTTPError as exc:
        raise IAPVerificationError("token_exchange_failed") from exc
    token = response.json().get("access_token")
    if not isinstance(token, str):
        raise IAPVerificationError("token_exchange_failed")
    return token


async def verify_purchase(*, client_id, client_secret, product_id, purchase_token, client=None):
    """Verify a Huawei AppGallery subscription purchase token. Returns the
    decoded purchaseTokenData dict. Raises IAPVerificationError if the
    purchase can't be confirmed active."""
    owns_client = client is None
    client = client or httpx.AsyncClient()
    try:
        access_token = await _access_token(client_id, client_secret, client)
        try:
            response = await client.post(
                VERIFY_URL,
                params={"access_token": access_token},
                json={"purchaseToken": purchase_token, "productId": product_id, "subscription": True},
                timeout=20,
            )
            response.raise_for_status()
        except httpx.HTTPError as exc:
            raise IAPVerificationError("purchase_lookup_failed") from exc
        data = response.json()
    finally:
        if owns_client:
            await client.aclose()

    if str(data.get("responseCode")) != "0":
        raise IAPVerificationError("purchase_lookup_failed")
    purchase = data.get("purchaseTokenData")
    if isinstance(purchase, str):
        try:
            purchase = json.loads(purchase)
        except ValueError as exc:
            raise IAPVerificationError("malformed_purchase_data") from exc
    if not isinstance(purchase, dict) or purchase.get("purchaseState") != 0:
        raise IAPVerificationError("subscription_not_active")
    return purchase
