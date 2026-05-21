import os
import traceback
from dotenv import load_dotenv
load_dotenv()

# Apply monkey patch BEFORE importing pywebpush
import cryptography.hazmat.primitives.asymmetric.ec as ec
import inspect

_orig_generate_private_key = ec.generate_private_key

def _patched_generate_private_key(curve, backend=None):
    if inspect.isclass(curve) and issubclass(curve, ec.EllipticCurve):
        curve = curve()
    return _orig_generate_private_key(curve, backend)

ec.generate_private_key = _patched_generate_private_key
print("Applied cryptography.hazmat.primitives.asymmetric.ec.generate_private_key monkey patch!")

from app import create_app
from app.extensions import db
from app.models.user import User
from app.models.notification import PushSubscription, Notification
from pywebpush import webpush, WebPushException

app = create_app()
with app.app_context():
    user_id = 7
    user = db.session.get(User, user_id)
    print("User found:", user)
    print("User.push_enabled:", user.push_enabled)
    
    subscriptions = PushSubscription.query.filter_by(user_id=user_id).all()
    print("Subscriptions count:", len(subscriptions))
        
    vapid_private_key = app.config.get('VAPID_PRIVATE_KEY', '').strip()
    vapid_claims      = app.config.get('VAPID_CLAIMS')
    
    from py_vapid import Vapid
    vapid_obj = None

    if "-----BEGIN" in vapid_private_key:
        try:
            vapid_obj = Vapid.from_pem(vapid_private_key.encode('utf-8'))
            print("Successfully loaded VAPID key from PEM format.")
        except Exception as e:
            print(f"Failed to parse VAPID key as PEM: {e}")

    if not vapid_obj:
        try:
            vapid_obj = Vapid.from_string(vapid_private_key)
            print("Successfully loaded VAPID key from raw base64url string.")
        except Exception as e:
            print(f"Failed to parse VAPID key as base64url string: {e}")

    if not vapid_obj:
        try:
            import base64
            padded = vapid_private_key + '=' * (4 - len(vapid_private_key) % 4)
            raw_bytes = base64.urlsafe_b64decode(padded)
            vapid_obj = Vapid.from_raw(raw_bytes)
            print("Successfully loaded VAPID key from base64-decoded raw bytes.")
        except Exception as e:
            print(f"All VAPID private key parsing attempts failed: {e}")

    if not vapid_obj:
        print("VAPID key parsing failed completely!")
    else:
        import json
        payload = json.dumps({
            "title": "Test Title",
            "body":  "Test Body",
            "data":  {"url": "/dashboard"}
        })
        for sub in subscriptions:
            sub_info = {
                "endpoint": sub.endpoint,
                "keys": {
                    "p256dh": sub.p256dh,
                    "auth":   sub.auth
                }
            }
            try:
                print(f"Attempting webpush for sub {sub.id}...")
                res = webpush(
                    subscription_info=sub_info,
                    data=payload,
                    vapid_private_key=vapid_obj,
                    vapid_claims=vapid_claims
                )
                print("Webpush response:", res)
            except WebPushException as ex:
                status_code = None
                if hasattr(ex, 'response') and ex.response is not None:
                    status_code = getattr(ex.response, 'status_code', None)
                print(f"WebPushException for sub {sub.id}: {ex} | Status code: {status_code}")
                if hasattr(ex, 'response') and ex.response is not None:
                    print("Response text:", ex.response.text)
            except Exception as ex:
                print(f"Unexpected error for sub {sub.id}: {ex}")
                traceback.print_exc()
