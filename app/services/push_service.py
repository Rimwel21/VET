import json
from flask import current_app
from pywebpush import webpush, WebPushException
from app.models.notification import PushSubscription

def send_push_notification(user_id, title, body, url="/dashboard", persist=True):
    """
    Sends a push notification to all registered subscriptions of the user if push is enabled.
    Also optionally persists the notification in the database as a local in-app notification.
    """
    from app.extensions import db
    from app.models.notification import Notification

    # Always persist as a local in-app notification first if requested
    if persist:
        try:
            note = Notification(user_id=user_id, title=title, message=body)
            db.session.add(note)
            db.session.commit()
        except Exception as e:
            db.session.rollback()
            current_app.logger.error(f"Failed to persist in-app notification: {e}")

    from app.models.user import User
    user = User.query.get(user_id)
    if not user or not user.push_enabled:
        return False

    subscriptions = PushSubscription.query.filter_by(user_id=user_id).all()
    if not subscriptions:
        return False
        
    vapid_private_key = current_app.config.get('VAPID_PRIVATE_KEY')
    vapid_claims = current_app.config.get('VAPID_CLAIMS')
    
    if not vapid_private_key:
        current_app.logger.error("VAPID_PRIVATE_KEY not configured")
        return False

    # VETSYNC SECURITY MATRIX: Raw VAPID Private Key Auto-Conversion
    # If the configured private key is a raw 43-character base64 URL-safe key,
    # we convert it to standard PEM format. This resolves pywebpush's internal
    # Python 3 concatenation bug that triggers a TypeError in from_raw().
    if "-----BEGIN PRIVATE KEY-----" not in vapid_private_key:
        try:
            from py_vapid import Vapid
            # Force conversion as bytes to avoid Python 3 type error inside py-vapid
            vapid_obj = Vapid.from_raw(vapid_private_key.encode('utf-8'))
            vapid_private_key = vapid_obj.private_pem().decode('utf-8')
        except Exception as e:
            current_app.logger.error(f"Failed to auto-convert VAPID private key to PEM: {e}")

    payload = json.dumps({
        "title": title,
        "body": body,
        "data": {"url": url}
    })

    success = False
    for sub in subscriptions:
        sub_info = {
            "endpoint": sub.endpoint,
            "keys": {
                "p256dh": sub.p256dh,
                "auth": sub.auth
            }
        }
        
        try:
            webpush(
                subscription_info=sub_info,
                data=payload,
                vapid_private_key=vapid_private_key,
                vapid_claims=vapid_claims
            )
            success = True
        except WebPushException as ex:
            current_app.logger.error(f"Web push failed: {repr(ex)}")
            # If subscription is expired/invalid (410 Gone or 404 Not Found), delete it
            status_code = getattr(ex.response, 'status_code', None) if hasattr(ex, 'response') else None
            if status_code in [404, 410] or "410 Gone" in str(ex) or "404 Not Found" in str(ex):
                from app.extensions import db
                db.session.delete(sub)
                db.session.commit()
                
    return success
