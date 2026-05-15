from datetime import datetime
from app.extensions import db

class AuditLog(db.Model):
    __tablename__ = 'audit_logs'

    id = db.Column(db.Integer, primary_key=True)
    timestamp = db.Column(db.DateTime, default=datetime.utcnow)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=True)
    user_name = db.Column(db.String(100), nullable=True) # Snapshot of name at time of action
    action_type = db.Column(db.String(50), nullable=False) # e.g., 'Auth Success', 'Booking Update', 'User Created'
    description = db.Column(db.Text, nullable=False)
    ip_address = db.Column(db.String(45), nullable=True)

    def to_dict(self):
        return {
            'id': self.id,
            'timestamp': self.timestamp.strftime('%Y-%m-%d %H:%M:%S'),
            'user': self.user_name or 'System',
            'action_type': self.action_type,
            'description': self.description,
            'ip_address': self.ip_address or 'internal'
        }
