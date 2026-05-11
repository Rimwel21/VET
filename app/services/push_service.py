import json
from flask import current_app
from pywebpush import webpush, WebPushException
from app.models.notification import PushSubscription

def send_push_notification(user_id, title, body, url="/dashboard"):
    """
    Sends a push notification to all devices registered by the user.
    """
    subscriptions = PushSubscription.query.filter_by(user_id=user_id).all()
    if not subscriptions:
        return False
        
    vapid_private_key = current_app.config.get('VAPID_PRIVATE_KEY')
    vapid_claims = current_app.config.get('VAPID_CLAIMS')
    
    if not vapid_private_key:
        current_app.logger.error("VAPID_PRIVATE_KEY not configured")
        return False

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
            # If subscription is expired/invalid, we could delete it here
            if ex.response and ex.response.status_code in [404, 410]:
                from app.extensions import db
                db.session.delete(sub)
                db.session.commit()
                
    return success
