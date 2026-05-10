from datetime import datetime, date
from flask import Blueprint, request, jsonify
from app.extensions import db
from app.models.booking import Booking
from app.models.service import Service
from app.middleware.decorators import jwt_required, role_required
from app.services.booking_service import booked_slots_on, get_no_show_risk, create_booking
from app.services.push_service import send_push_notification

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
    data     = request.get_json()
    required = ['service_id', 'slot', 'date', 'name', 'email', 'phone', 'pet_type']
    if not all(f in data for f in required):
        return jsonify({'error': 'Missing required fields'}), 400

    try:
        booking_date = datetime.strptime(data['date'], '%Y-%m-%d').date()
    except ValueError:
        return jsonify({'error': 'Invalid date format'}), 400

    if booking_date < date.today():
        return jsonify({'error': 'Cannot book a date in the past'}), 400

    if data['slot'] in booked_slots_on(booking_date):
        return jsonify({'error': f"Sorry! {data['slot']} on {data['date']} was just booked."}), 409

    if not db.session.get(Service, data['service_id']):
        return jsonify({'error': 'Invalid service selected.'}), 400

    data['date'] = booking_date
    booking = create_booking(data, current_user_jwt.id)
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
