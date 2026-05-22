import os
from dotenv import load_dotenv
load_dotenv()

from app import create_app
from app.models.audit_log import AuditLog

app = create_app(os.getenv('FLASK_ENV', 'default'))

with app.app_context():
    logs = AuditLog.query.order_by(AuditLog.timestamp.desc()).limit(30).all()
    print(f"Retrieved {len(logs)} audit logs:")
    for log in logs:
        print(f"Time: {log.timestamp} | User: {log.user_name} (ID: {log.user_id}) | Action: {log.action_type} | Desc: {log.description} | IP: {log.ip_address}")
