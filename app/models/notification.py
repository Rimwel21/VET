from datetime import datetime
from app.extensions import db


class Notification(db.Model):
    __tablename__ = 'notifications'

    id         = db.Column(db.Integer, primary_key=True)
    user_id    = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    title      = db.Column(db.String(100), nullable=False)
    message    = db.Column(db.Text,        nullable=False)
    read       = db.Column(db.Boolean,     default=False)
    created_at = db.Column(db.DateTime,    default=datetime.utcnow)


class PushSubscription(db.Model):
    __tablename__ = 'push_subscriptions'

    id         = db.Column(db.Integer, primary_key=True)
    user_id    = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    endpoint   = db.Column(db.Text,        nullable=False)
    p256dh     = db.Column(db.String(255), nullable=False)
    auth       = db.Column(db.String(255), nullable=False)
    created_at = db.Column(db.DateTime,    default=datetime.utcnow)
