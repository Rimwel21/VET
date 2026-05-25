from datetime import datetime, date
from flask import Blueprint, render_template, request, redirect, url_for, flash
from app.extensions import db
from app.models.service import Service
from app.models.booking import Booking
from app.middleware.decorators import login_required, _get_current_user
from app.services.booking_service import booked_slots_on, create_booking, ALL_SLOTS, PET_TYPES
from app.services.email_service import send_booking_email
from app.utils.validation import (
    FieldSpec,
    ValidationError,
    validate_choice,
    validate_email,
    validate_fields,
)

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
    try:
        # SECURITY: Booking payload validation.
        # Screens appointment, owner, pet, and medical free-text fields so users can
        # submit normal booking details while malicious payloads are rejected early.
        payload = validate_fields(request.form, {
            'name': FieldSpec(required=True, max_length=120),
            'email': FieldSpec(kind='email', required=True, max_length=120, escape_html=False),
            'phone': FieldSpec(kind='phone', required=True, max_length=30, escape_html=False),
            'alt_phone': FieldSpec(kind='phone', required=False, max_length=30, escape_html=False),
            'address': FieldSpec(required=False, max_length=255),
            'pet_name': FieldSpec(required=False, max_length=80),
            'pet_type': FieldSpec(kind='choice', required=True, choices=tuple(PET_TYPES), escape_html=False),
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
            'service': FieldSpec(required=True, max_length=20, escape_html=False),
            'slot': FieldSpec(required=True, max_length=20, escape_html=False),
            'date': FieldSpec(required=True, max_length=10, escape_html=False),
        })
    except ValidationError as exc:
        flash(exc.message, 'error')
        return redirect(url_for('booking.booking_page'))

    name = payload['name']
    email = payload['email']
    phone = payload['phone']
    pet_type = payload['pet_type']
    service_id = payload['service']
    slot = payload['slot']
    date_str = payload['date']

    if not all([name, email, phone, pet_type, service_id, slot, date_str]):
        flash('Please fill in all required fields.', 'error')
        return redirect(url_for('booking.booking_page'))

    try:
        booking_date = datetime.strptime(date_str, '%Y-%m-%d').date()
        service_id_int = int(service_id)
    except ValueError:
        flash('Invalid booking details selected.', 'error')
        return redirect(url_for('booking.booking_page'))

    if booking_date < date.today():
        flash('Cannot book a date in the past.', 'error')
        return redirect(url_for('booking.booking_page'))

    try:
        # SECURITY: Business-rule validation.
        # Confirms the selected slot and email format are valid application values,
        # preventing tampered booking submissions from bypassing UI constraints.
        slot = validate_choice(slot, field='slot', choices=tuple(ALL_SLOTS))
        email = validate_email(email)
    except ValidationError as exc:
        flash(exc.message, 'error')
        return redirect(url_for('booking.booking_page'))

    if slot in booked_slots_on(booking_date):
        flash(f'Sorry! {slot} on {booking_date.strftime("%b %d")} was just booked. Choose another slot.', 'error')
        return redirect(url_for('booking.booking_page'))

    service = db.session.get(Service, service_id_int)
    if not service:
        flash('Invalid service selected.', 'error')
        return redirect(url_for('booking.booking_page'))

    user = _get_current_user()
    data = {
        'service_id': service.id, 'slot': slot, 'date': booking_date,
        'name': name, 'email': email, 'phone': phone,
        'alt_phone': payload['alt_phone'], 'address': payload['address'],
        'pet_name': payload['pet_name'], 'pet_type': pet_type,
        'pet_breed': payload['pet_breed'], 'pet_sex': payload['pet_sex'],
        'pet_age': payload['pet_age'], 'pet_weight': payload['pet_weight'], 'pet_color': payload['pet_color'],
        'visit_reason': payload['visit_reason'], 'medical_history': payload['medical_history'],
        'allergies': payload['allergies'], 'notes': payload['notes'],
        'payment_method': payload['payment_method'],
        'consent': request.form.get('consent') == 'on',
    }

    new_booking = create_booking(data, user.id)
    flash(
        f'Booking submitted. {service.name} for {payload["pet_name"] or "your pet"} '
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
    send_booking_email(booking, 'cancelled')
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
