import os
from dotenv import load_dotenv
load_dotenv()

from app import create_app
from app.models.user import User

app = create_app(os.getenv('FLASK_ENV', 'default'))

with app.app_context():
    user = User.query.filter_by(email="adminvetclinic@gmail.com").first()
    if user:
        print(f"User: {user.email}")
        is_correct = user.check_password("vetadminclinic1214")
        print(f"Password 'vetadminclinic1214' check: {is_correct}")
        
        # Let's also check other common passwords or inspect the hash
        print(f"Password hash: {user.password_hash}")
    else:
        print("User not found!")
