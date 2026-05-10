from datetime import datetime
from app.extensions import db


class ContactMessage(db.Model):
    __tablename__ = 'contact_messages'

    id         = db.Column(db.Integer, primary_key=True)
    name       = db.Column(db.String(120), nullable=False)
    email      = db.Column(db.String(120), nullable=False)
    subject    = db.Column(db.String(200))
    message    = db.Column(db.Text,        nullable=False)
    created_at = db.Column(db.DateTime,    default=datetime.utcnow)
