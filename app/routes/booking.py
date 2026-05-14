from datetime import datetime, date
from flask import Blueprint, render_template, request, redirect, url_for, flash
from app.extensions import db
from app.models.service import Service
from app.models.booking import Booking
from app.middleware.decorators import login_required, _get_current_user
from app.services.booking_service import booked_slots_on, create_booking, ALL_SLOTS, PET_TYPES
from app.utils.sanitize import clean_input

booking_bp = Blueprint('booking', __name__)


@booking_bp.route('/booking')
@login_required
def booking_page():
    user = _get_current_user()
    if user.role != 'client':
        flash('Only clients can book appointments online.', 'info')
        dest = 'dashboard.admin_dashboard' if user.role == 'admin' else 'dashboard.staff_dashboard'
        return redirect(url_for(dest))

    services   = Service.query.all()
    today      = date.today().isoformat()
    service_id = request.args.get('service_id', 0, type=int)  # ← add this

    return render_template('booking_page.html', user=user,
                           services=services, pet_types=PET_TYPES, today=today,
                           preselected_service=service_id)


@booking_bp.route('/book', methods=['POST'])
@login_required
def book():
    g = lambda k: clean_input(request.form.get(k, ''))

    name       = g('name')
    email      = g('email')
    phone      = g('phone')
    pet_type   = g('pet_type')
    service_id = g('service')
    slot       = g('slot')
    date_str   = g('date')

    if not all([name, email, phone, pet_type, service_id, slot, date_str]):
        flash('Please fill in all required fields.', 'error')
        return redirect(url_for('booking.booking_page'))

    try:
        booking_date = datetime.strptime(date_str, '%Y-%m-%d').date()
    except ValueError:
        flash('Invalid date selected.', 'error')
        return redirect(url_for('booking.booking_page'))

    if booking_date < date.today():
        flash('Cannot book a date in the past.', 'error')
        return redirect(url_for('booking.booking_page'))

    if slot in booked_slots_on(booking_date):
        flash(f'Sorry! {slot} on {booking_date.strftime("%b %d")} was just booked. Choose another slot.', 'error')
        return redirect(url_for('booking.booking_page'))

    service = db.session.get(Service, service_id)
    if not service:
        flash('Invalid service selected.', 'error')
        return redirect(url_for('booking.booking_page'))

    user = _get_current_user()
    data = {
        'service_id': service.id, 'slot': slot, 'date': booking_date,
        'name': name, 'email': email, 'phone': phone,
        'alt_phone': g('alt_phone'), 'address': g('address'),
        'pet_name': g('pet_name'), 'pet_type': pet_type,
        'pet_breed': g('pet_breed'), 'pet_sex': g('pet_sex'),
        'pet_age': g('pet_age'), 'pet_weight': g('pet_weight'), 'pet_color': g('pet_color'),
        'visit_reason': g('visit_reason'), 'medical_history': g('medical_history'),
        'allergies': g('allergies'), 'notes': g('notes'),
        'payment_method': g('payment_method'),
        'consent': request.form.get('consent') == 'on',
    }

    new_booking = create_booking(data, user.id)
    flash(
        f'Booking submitted. {service.name} for {g("pet_name") or "your pet"} '
        f'on {booking_date.strftime("%B %d, %Y")} at {slot} is now pending staff confirmation.',
        'success'
    )
    return redirect(url_for('dashboard.client_dashboard'))


@booking_bp.route('/booking/cancel/<int:bid>', methods=['POST'])
@login_required
def cancel_booking(bid):
    user    = _get_current_user()
    booking = db.session.get(Booking, bid)
    if not booking or booking.user_id != user.id:
        flash('Unauthorized.', 'error')
        return redirect(url_for('dashboard.client_dashboard'))

    if booking.status != 'pending':
        flash('This booking can no longer be cancelled because staff already accepted it.', 'error')
        return redirect(url_for('dashboard.client_dashboard'))

    booking.status = 'cancelled'
    db.session.commit()
    flash('Booking cancelled successfully.', 'success')
    return redirect(url_for('dashboard.client_dashboard'))


@booking_bp.route('/api/available-slots')
def available_slots():
    from flask import jsonify
    date_str = request.args.get('date', '')
    try:
        q_date = datetime.strptime(date_str, '%Y-%m-%d').date()
    except ValueError:
        return jsonify({'error': 'Invalid date'}), 400

    if q_date < date.today():
        return jsonify({'date': date_str, 'slots': [{'time': s, 'available': False} for s in ALL_SLOTS]})

    taken = booked_slots_on(q_date)
    return jsonify({
        'date': date_str,
        'slots': [{'time': s, 'available': s not in taken} for s in ALL_SLOTS]
    })


@booking_bp.route('/api/services')
def get_services():
    from flask import jsonify
    return jsonify([{'id': s.id, 'name': s.name, 'icon': s.icon} for s in Service.query.all()])
