from app import create_app
from app.extensions import db
import os

# Create the app instance
app = create_app('development')

with app.app_context():
    print("Checking for audit_logs table...")
    try:
        from app.models.audit_log import AuditLog
        db.create_all()
        print("Success: AuditLog table verified/created.")
    except Exception as e:
        print(f"Error creating AuditLog table: {e}")
