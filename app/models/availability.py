from app.extensions import db


class DoctorAvailability(db.Model):
    __tablename__ = 'doctor_availability'

    id     = db.Column(db.Integer, primary_key=True)
    date   = db.Column(db.Date,        nullable=False)
    slot   = db.Column(db.String(20),  nullable=False)
    status = db.Column(db.String(20),  default='unavailable')
