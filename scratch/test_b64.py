import os
import base64
from dotenv import load_dotenv
load_dotenv()

from app import create_app
from app.extensions import db
from app.models.notification import PushSubscription

app = create_app()
with app.app_context():
    subscriptions = PushSubscription.query.filter_by(user_id=7).all()
    for sub in subscriptions:
        print(f"Sub ID: {sub.id}")
        try:
            p256dh_bytes = base64.b64decode(sub.p256dh)
            print("p256dh b64decode success, bytes length:", len(p256dh_bytes))
            # Convert bytes to base64url string
            p256dh_url = base64.urlsafe_b64encode(p256dh_bytes).decode('utf-8')
            print("p256dh_url:", p256dh_url[:30])
        except Exception as e:
            print("p256dh b64decode failed:", e)
            
        try:
            auth_bytes = base64.b64decode(sub.auth)
            print("auth b64decode success, bytes length:", len(auth_bytes))
            auth_url = base64.urlsafe_b64encode(auth_bytes).decode('utf-8')
            print("auth_url:", auth_url[:30])
        except Exception as e:
            print("auth b64decode failed:", e)
