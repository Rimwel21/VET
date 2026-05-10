from datetime import datetime
from app.extensions import db


class Booking(db.Model):
    __tablename__ = 'bookings'

    id              = db.Column(db.Integer, primary_key=True)

    # Appointment
    service_id      = db.Column(db.Integer, db.ForeignKey('services.id'), nullable=False)
    slot            = db.Column(db.String(20),  nullable=False)
    date            = db.Column(db.Date,        nullable=False)

    # Owner info
    name            = db.Column(db.String(120), nullable=False)
    email           = db.Column(db.String(120), nullable=False)
    phone           = db.Column(db.String(30),  nullable=False)
    alt_phone       = db.Column(db.String(30))
    address         = db.Column(db.String(255))

    # Pet info
    pet_name        = db.Column(db.String(80))
    pet_type        = db.Column(db.String(50),  nullable=False)
    pet_breed       = db.Column(db.String(100))
    pet_sex         = db.Column(db.String(30))
    pet_age         = db.Column(db.String(30))
    pet_weight      = db.Column(db.String(20))
    pet_color       = db.Column(db.String(100))

    # Medical
    visit_reason    = db.Column(db.Text)
    medical_history = db.Column(db.Text)
    allergies       = db.Column(db.String(255))
    notes           = db.Column(db.Text)

    # Payment & consent
    payment_method  = db.Column(db.String(50))
    consent         = db.Column(db.Boolean, default=False)

    # Meta
    status          = db.Column(db.String(20),  default='pending')
    user_id         = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=True)
    handled_by      = db.Column(db.String(100), nullable=True)
    created_at      = db.Column(db.DateTime,    default=datetime.utcnow)

    @property
    def no_show_risk(self):
        """Calculates risk based on client's past cancellations."""
        cancellations = Booking.query.filter_by(email=self.email, status='cancelled').count()
        return cancellations > 1
