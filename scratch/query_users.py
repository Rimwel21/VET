import os
from dotenv import load_dotenv
load_dotenv()

from app import create_app
from app.models.user import User

app = create_app(os.getenv('FLASK_ENV', 'default'))

with app.app_context():
    users = User.query.all()
    print(f"Total users found: {len(users)}")
    for user in users:
        print(f"ID: {user.id} | Name: {user.first_name} {user.last_name} | Email: {user.email} | Role: {user.role} | Active: {user.is_active}")
