from datetime import datetime, date
from flask import Blueprint, request, jsonify
from app.extensions import db
from app.models.booking import Booking
from app.models.service import Service
from app.middleware.decorators import jwt_required, role_required
from app.services.booking_service import booked_slots_on, get_no_show_risk, create_booking, ALL_SLOTS
from app.services.push_service import send_push_notification
from app.utils.validation import (
    FieldSpec,
    ValidationError,
    validate_choice,
    validate_email,
    validate_fields,
)

api_appointments_bp = Blueprint('api_appointments', __name__)


@api_appointments_bp.route('', methods=['GET', 'POST'])
@jwt_required
def appointments(current_user_jwt):
    if request.method == 'GET':
        if current_user_jwt.role in ['admin', 'staff']:
            bookings = Booking.query.all()
        else:
            bookings = Booking.query.filter_by(user_id=current_user_jwt.id).all()

        return jsonify([{
            'id': b.id, 'service_id': b.service_id, 'slot': b.slot,
            'date': b.date.isoformat(), 'name': b.name, 'email': b.email,
            'phone': b.phone, 'pet_name': b.pet_name, 'pet_type': b.pet_type,
            'status': b.status, 'user_id': b.user_id,
            'no_show_risk': get_no_show_risk(b.email)
        } for b in bookings]), 200

    # POST
    data = request.get_json() or {}
    required = ['service_id', 'slot', 'date', 'name', 'email', 'phone', 'pet_type']
    if not all(f in data for f in required):
        return jsonify({'error': 'Missing required fields'}), 400

    try:
        normalized = validate_fields(data, {
            'name': FieldSpec(required=True, max_length=120),
            'email': FieldSpec(kind='email', required=True, max_length=120, escape_html=False),
            'phone': FieldSpec(kind='phone', required=True, max_length=30, escape_html=False),
            'pet_type': FieldSpec(required=True, max_length=50, escape_html=False),
            'pet_name': FieldSpec(required=False, max_length=80),
            'slot': FieldSpec(required=True, max_length=20, escape_html=False),
            'date': FieldSpec(required=True, max_length=10, escape_html=False),
            'alt_phone': FieldSpec(kind='phone', required=False, max_length=30, escape_html=False),
            'address': FieldSpec(required=False, max_length=255),
            'pet_breed': FieldSpec(required=False, max_length=100),
            'pet_sex': FieldSpec(required=False, max_length=30),
            'pet_age': FieldSpec(required=False, max_length=30),
            'pet_weight': FieldSpec(required=False, max_length=20),
            'pet_color': FieldSpec(required=False, max_length=100),
            'visit_reason': FieldSpec(required=False, max_length=1500, allow_newlines=True),
            'medical_history': FieldSpec(required=False, max_length=3000, allow_newlines=True),
            'allergies': FieldSpec(required=False, max_length=255),
            'notes': FieldSpec(required=False, max_length=1500, allow_newlines=True),
            'payment_method': FieldSpec(required=False, max_length=50),
        })
        normalized['slot'] = validate_choice(normalized['slot'], field='slot', choices=tuple(ALL_SLOTS))
        normalized['email'] = validate_email(normalized['email'])
    except ValidationError as exc:
        return jsonify({'error': exc.message, 'field': exc.field}), exc.code

    try:
        booking_date = datetime.strptime(normalized['date'], '%Y-%m-%d').date()
        service_id = int(data['service_id'])
    except ValueError:
        return jsonify({'error': 'Invalid booking payload'}), 400

    if booking_date < date.today():
        return jsonify({'error': 'Cannot book a date in the past'}), 400

    if normalized['slot'] in booked_slots_on(booking_date):
        return jsonify({'error': f"Sorry! {normalized['slot']} on {normalized['date']} was just booked."}), 409

    if not db.session.get(Service, service_id):
        return jsonify({'error': 'Invalid service selected.'}), 400

    booking_payload = dict(data)
    booking_payload.update(normalized)
    booking_payload['service_id'] = service_id
    booking_payload['date'] = booking_date
    booking = create_booking(booking_payload, current_user_jwt.id)
    
    # Notify staff
    from app.models.user import User
    staff_users = User.query.filter(User.role.in_(['staff', 'admin'])).all()
    for staff in staff_users:
        send_push_notification(
            staff.id,
            "New Booking Alert",
            f"A new booking request from {booking_payload['name']} for {booking_payload.get('pet_name')} on {booking_payload['date']}."
        )

    return jsonify({'message': 'Booking created successfully', 'booking_id': booking.id}), 201


@api_appointments_bp.route('/<int:booking_id>', methods=['PUT'])
@role_required(['staff', 'admin'])
def update_appointment(current_user_jwt, booking_id):
    booking = db.session.get(Booking, booking_id)
    if not booking:
        return jsonify({'error': 'Booking not found'}), 404

    data = request.get_json()
    if 'status' in data:
        if data['status'] not in ['confirmed', 'pending', 'cancelled', 'completed']:
            return jsonify({'error': 'Invalid status'}), 400
        booking.status = data['status']
        if booking.user_id:
            send_push_notification(
                booking.user_id,
                "Appointment Update",
                f"Your booking for {booking.pet_name} is now {booking.status}."
            )

    db.session.commit()
    return jsonify({'message': 'Booking updated successfully', 'status': booking.status}), 200


@api_appointments_bp.route('/<int:booking_id>', methods=['DELETE'])
@role_required(['staff', 'admin'])
def delete_appointment(current_user_jwt, booking_id):
    booking = db.session.get(Booking, booking_id)
    if not booking:
        return jsonify({'error': 'Booking not found'}), 404
    db.session.delete(booking)
    db.session.commit()
    return jsonify({'message': 'Booking removed successfully'}), 200


@api_appointments_bp.route('/all', methods=['GET'])
@role_required(['admin', 'staff'])
def get_all_appointments(current_user_jwt):
    bookings = Booking.query.order_by(Booking.date.desc(), Booking.slot.desc()).all()
    return jsonify([{
        'id': b.id, 'date': b.date.isoformat(), 'slot': b.slot,
        'pet_name': b.pet_name or 'N/A', 'name': b.name,
        'service_id': b.service_id,
        'service_name': b.service_ref.name if b.service_ref else 'Unknown',
        'status': b.status,
        'handled_by': b.handled_by or 'System / Not Recorded'
    } for b in bookings]), 200
