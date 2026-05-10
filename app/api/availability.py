from datetime import datetime
from flask import Blueprint, request, jsonify
from app.extensions import db
from app.models.availability import DoctorAvailability
from app.middleware.decorators import role_required

api_availability_bp = Blueprint('api_availability', __name__)


@api_availability_bp.route('', methods=['GET'])
@role_required(['staff', 'admin'])
def get_schedule(current_user_jwt):
    blocks = DoctorAvailability.query.all()
    return jsonify([{'date': b.date.isoformat(), 'slot': b.slot, 'status': b.status} for b in blocks]), 200


@api_availability_bp.route('/block', methods=['POST'])
@role_required(['staff', 'admin'])
def block_time(current_user_jwt):
    data = request.get_json()
    try:
        d = datetime.strptime(data['date'], '%Y-%m-%d').date()
    except Exception:
        return jsonify({'error': 'Invalid date format'}), 400

    if not DoctorAvailability.query.filter_by(date=d, slot=data['slot']).first():
        db.session.add(DoctorAvailability(date=d, slot=data['slot'], status='unavailable'))
        db.session.commit()
    return jsonify({'message': 'Time slot blocked successfully'}), 201


@api_availability_bp.route('/unblock', methods=['DELETE'])
@role_required(['staff', 'admin'])
def unblock_time(current_user_jwt):
    data = request.get_json()
    try:
        d = datetime.strptime(data['date'], '%Y-%m-%d').date()
    except Exception:
        return jsonify({'error': 'Invalid date format'}), 400

    existing = DoctorAvailability.query.filter_by(date=d, slot=data['slot']).first()
    if existing:
        db.session.delete(existing)
        db.session.commit()
    return jsonify({'message': 'Time slot is now available'}), 200


@api_availability_bp.route('/workload', methods=['GET'])
@role_required(['staff', 'admin'])
def get_workload(current_user_jwt):
    from datetime import date, datetime
    from app.models.booking import Booking
    from sqlalchemy import extract

    today = date.today()
    year = request.args.get('year', default=today.year, type=int)
    month = request.args.get('month', default=today.month, type=int)
    granularity = request.args.get('granularity', default='hourly')

    bookings = Booking.query.filter(
        extract('year', Booking.date) == year,
        extract('month', Booking.date) == month,
        Booking.status == 'confirmed'
    ).all()

    counts = {}
    total_confirmed = len(bookings)

    for b in bookings:
        if granularity == 'hourly':
            try:
                # Convert "9:00 AM" to actual time object
                t = datetime.strptime(b.slot, "%I:%M %p").time()
                dt = datetime.combine(b.date, t)
                key = dt.isoformat()
            except:
                key = datetime.combine(b.date, datetime.min.time()).isoformat()
        else: # daily
            key = b.date.isoformat()
            
        counts[key] = counts.get(key, 0) + 1

    data_points = [{'x': k, 'y': v} for k, v in counts.items()]
    data_points.sort(key=lambda item: item['x'])

    # Determine percentage (simplistic logic based on max capacity)
    import calendar
    _, days_in_month = calendar.monthrange(year, month)
    max_slots = days_in_month * 14
    percentage = round((total_confirmed / max_slots) * 100, 1) if max_slots else 0

    return jsonify({
        'data_points': data_points,
        'total_confirmed': total_confirmed,
        'percentage': percentage,
        'granularity': granularity
    }), 200
