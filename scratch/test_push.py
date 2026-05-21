import os
from dotenv import load_dotenv
load_dotenv()

from app import create_app
from app.extensions import db
from app.services.push_service import send_push_notification

app = create_app()
with app.app_context():
    print("Sending test push notification to user 7...")
    res = send_push_notification(7, "Test Title", "Test Body from script", persist=False)
    print("Result:", res)
