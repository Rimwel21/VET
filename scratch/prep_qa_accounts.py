import os
from app import create_app
from app.extensions import db
from app.models.user import User

app = create_app('default')
with app.app_context():
    # Admin
    admin = User.query.filter_by(email='admin@vetsync.com').first()
    if not admin:
        admin = User(first_name='Admin', last_name='User', email='admin@vetsync.com', role='admin')
    admin.set_password('admin123')
    
    # Staff
    staff = User.query.filter_by(email='staff@vetsync.com').first()
    if not staff:
        staff = User(first_name='Staff', last_name='User', email='staff@vetsync.com', role='staff')
    staff.set_password('staff123')
    
    db.session.add(admin)
    db.session.add(staff)
    db.session.commit()
    print("TEST_ACCOUNTS_READY")
