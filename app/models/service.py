from app.extensions import db


class Service(db.Model):
    __tablename__ = 'services'

    id       = db.Column(db.Integer, primary_key=True)
    name     = db.Column(db.String(100), nullable=False)
    icon     = db.Column(db.String(10))
    desc     = db.Column(db.Text)
    bookings = db.relationship('Booking', backref='service_ref', lazy=True)
