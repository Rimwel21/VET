from datetime import datetime, timedelta
from app.extensions import db

class OtpVerification(db.Model):
    __tablename__ = 'otp_verifications'

    id         = db.Column(db.Integer, primary_key=True)
    user_id    = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=True)
    email      = db.Column(db.String(120), index=True, nullable=False)
    otp_code   = db.Column(db.String(255), nullable=False)  # Hashed
    expires_at = db.Column(db.DateTime, nullable=False)
    is_used    = db.Column(db.Boolean, default=False)
    attempts   = db.Column(db.Integer, default=0)
    reset_token = db.Column(db.String(255), nullable=True)
    token_expires_at = db.Column(db.DateTime, nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    def is_expired(self):
        return datetime.utcnow() > self.expires_at

    def __repr__(self):
        return f'<OtpVerification {self.email} - {self.is_used}>'
