from datetime import datetime
from werkzeug.security import generate_password_hash, check_password_hash
from app.extensions import db


class User(db.Model):
    __tablename__ = 'users'

    id            = db.Column(db.Integer, primary_key=True)
    first_name    = db.Column(db.String(80),  nullable=False)
    last_name     = db.Column(db.String(80),  nullable=False)
    email         = db.Column(db.String(120), unique=True, nullable=False)
    contact       = db.Column(db.String(30))
    password_hash = db.Column(db.String(256), nullable=False)
    role          = db.Column(db.String(20),  default='client')  # client, staff, admin
    is_active     = db.Column(db.Boolean,     default=True)
    created_at    = db.Column(db.DateTime,    default=datetime.utcnow)

    bookings      = db.relationship('Booking',      backref='user', lazy=True)
    notifications = db.relationship('Notification', backref='user', lazy=True)

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)
