from workflows.workflows.api.shopify import _verify_hmac


def test_hmac_verification_roundtrip():
    raw = b'{"a":1}'
    secret = "x"
    import base64, hmac, hashlib
    sig = base64.b64encode(hmac.new(secret.encode(), raw, hashlib.sha256).digest()).decode()
    assert _verify_hmac(raw, sig, secret) is True
