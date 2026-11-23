"""IAP (in-app purchase) -> kurt/saas Store.grant(), for mobile App Store /
Google Play / Huawei AppGallery subscriptions.

Each provider module (iap_apple.py, iap_google.py, iap_huawei.py) verifies
its own store's receipt/transaction/purchase token; this module maps the
verified product id to a (plan, days) pair and calls the SAME
`Store.grant()` primitive `kurt/saas/admin.py` already uses for
operator-issued subscriptions. Buying via a store is another way to reach
the same entitlement system, not a new one.
"""

PRODUCT_PLANS = {
    "kurt_pro_monthly": ("pro", 31),
    "kurt_pro_yearly": ("pro", 366),
    "kurt_starter_monthly": ("starter", 31),
}


class IAPVerificationError(Exception):
    pass


def plan_for_product(product_id):
    try:
        return PRODUCT_PLANS[product_id]
    except KeyError:
        raise IAPVerificationError(f"unknown_product:{product_id}")
