from flask import request
from app.extensions import db
from app.models.audit_log import AuditLog
from app.middleware.decorators import _get_current_user

def log_action(action_type, description, user=None):
    """
    Utility function to log an action to the AuditLog table.
    """
    if user is None:
        user = _get_current_user()

    user_id = user.id if user else None
    user_name = f"{user.first_name} {user.last_name}" if user else "System"
    
    # Try to get IP address
    ip_address = request.remote_addr if request else "internal"
    
    # Special case for proxied requests (if applicable)
    if request and request.headers.get('X-Forwarded-For'):
        ip_address = request.headers.get('X-Forwarded-For').split(',')[0]

    log_entry = AuditLog(
        user_id=user_id,
        user_name=user_name,
        action_type=action_type,
        description=description,
        ip_address=ip_address
    )
    
    try:
        db.session.add(log_entry)
        db.session.commit()
    except Exception as e:
        print(f"Error logging action: {e}")
        db.session.rollback()
