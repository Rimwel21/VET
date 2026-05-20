from datetime import datetime
from werkzeug.security import generate_password_hash, check_password_hash
from app.extensions import db


# VETSYNC SECURITY MATRIX: SQL Injection (SQLi) Prevention
# All database operations on the User model are performed via SQLAlchemy's ORM (db.Model).
# This enforces strict query parameterization globally. User-supplied inputs (like email, 
# first name, etc.) are treated strictly as data payloads rather than executable command 
# segments, completely neutralizing SQL Injection exploits.
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
    push_enabled  = db.Column(db.Boolean,     default=True, server_default='1')
    created_at    = db.Column(db.DateTime,    default=datetime.utcnow)

    bookings      = db.relationship('Booking',      backref='user', lazy=True)
    notifications = db.relationship('Notification', backref='user', lazy=True)

    def __init__(self, first_name=None, last_name=None, email=None, contact=None, role='client', is_active=True, push_enabled=True, **kwargs):
        super().__init__(
            first_name=first_name,
            last_name=last_name,
            email=email,
            contact=contact,
            role=role,
            is_active=is_active,
            push_enabled=push_enabled,
            **kwargs
        )

    # VETSYNC SECURITY MATRIX: Password Hashing (Salted & Encrypted)
    # Standard passwords are never stored in raw text. They are immediately salted 
    # and run through a secure one-way hashing algorithm (PBKDF2 with SHA256) via 
    # werkzeug.security to prevent reversal even in the event of a raw database breach.
    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)

