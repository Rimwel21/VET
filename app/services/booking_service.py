from datetime import date as date_type
from app.extensions import db
from app.models.booking import Booking

ALL_SLOTS = ["9:00 AM", "10:00 AM", "11:00 AM", "1:00 PM", "2:00 PM", "3:00 PM", "4:00 PM"]
PET_TYPES = ["Dog", "Cat", "Bird", "Rabbit", "Reptile", "Fish", "Other"]


def booked_slots_on(q_date: date_type) -> set:
    """Returns set of already-booked slot strings for a given date."""
    taken = Booking.query.filter(
        Booking.date == q_date,
        Booking.status.in_(['pending', 'confirmed'])
    ).all()
    return {b.slot for b in taken}


def get_no_show_risk(email: str) -> bool:
    """Predicts risk based on client's cancellation history."""
    if not email:
        return False
    cancellations = Booking.query.filter_by(email=email, status='cancelled').count()
    return cancellations > 1


def create_booking(data: dict, user_id: int) -> Booking:
    """
    Creates and persists a Booking from a flat data dict.
    Caller is responsible for validating required fields and slot availability beforehand.
    """
    booking = Booking(
        service_id      = data['service_id'],
        slot            = data['slot'],
        date            = data['date'],
        name            = data['name'],
        email           = data['email'],
        phone           = data['phone'],
        alt_phone       = data.get('alt_phone'),
        address         = data.get('address'),
        pet_name        = data.get('pet_name'),
        pet_type        = data['pet_type'],
        pet_breed       = data.get('pet_breed'),
        pet_sex         = data.get('pet_sex'),
        pet_age         = data.get('pet_age'),
        pet_weight      = data.get('pet_weight'),
        pet_color       = data.get('pet_color'),
        visit_reason    = data.get('visit_reason'),
        medical_history = data.get('medical_history'),
        allergies       = data.get('allergies'),
        notes           = data.get('notes'),
        payment_method  = data.get('payment_method'),
        consent         = data.get('consent', False),
        status          = 'pending',
        user_id         = user_id,
    )
    db.session.add(booking)
    db.session.commit()
    return booking
