import os
from app import create_app
from app.extensions import db
from app.models.user import User

app = create_app('default')
with app.app_context():
    users = User.query.all()
    print("USER_LIST_START")
    for u in users:
        print(f"{u.email} | {u.role} | {u.first_name} {u.last_name}")
    print("USER_LIST_END")
