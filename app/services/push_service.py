import json
from flask import current_app
from pywebpush import webpush, WebPushException
from app.extensions import db
from app.models.notification import PushSubscription


def send_push_notification(user_id: int, title: str, body: str, url: str = None):
    """Sends a web push notification to all subscribed devices of a user."""
    subscriptions = PushSubscription.query.filter_by(user_id=user_id).all()
    payload = {
        "title": title,
        "body": body,
        "icon": "/static/images/vet-dog.png",
        "data": {"url": url or "/dashboard"}
    }

    for sub in subscriptions:
        try:
            webpush(
                subscription_info={
                    "endpoint": sub.endpoint,
                    "keys": {"p256dh": sub.p256dh, "auth": sub.auth}
                },
                data=json.dumps(payload),
                vapid_private_key=current_app.config['VAPID_PRIVATE_KEY'],
                vapid_claims=current_app.config['VAPID_CLAIMS']
            )
        except WebPushException as ex:
            print(f"Push failed for user {user_id}: {ex}")
            if ex.response and ex.response.status_code in [404, 410]:
                db.session.delete(sub)
                db.session.commit()
        except Exception as e:
            print(f"Unexpected push error: {e}")
