import json
from datetime import date
from flask import Blueprint, render_template, redirect, url_for
from app.extensions import db
from app.models.booking import Booking
from app.models.user import User
from app.middleware.decorators import login_required, admin_required, staff_required, _get_current_user

dashboard_bp = Blueprint('dashboard', __name__)


@dashboard_bp.route('/dashboard')
@login_required
def dashboard():
    user = _get_current_user()
    if user.role == 'admin':
        return redirect(url_for('dashboard.admin_dashboard'))
    elif user.role == 'staff':
        return redirect(url_for('dashboard.staff_dashboard'))
    return redirect(url_for('dashboard.client_dashboard'))


@dashboard_bp.route('/dashboard/client')
@login_required
def client_dashboard():
    user     = _get_current_user()
    bookings = (Booking.query
                .filter_by(user_id=user.id)
                .order_by(Booking.created_at.desc())
                .all())
    return render_template('dashboard.html', user=user, bookings=bookings)


@dashboard_bp.route('/dashboard/profile', methods=['GET', 'POST'])
@login_required
def profile():
    from flask import request, flash
    from app.utils.sanitize import clean_input
    
    user = _get_current_user()
    
    if request.method == 'POST':
        # Simple update logic for contact
        contact = clean_input(request.form.get('contact', ''))
        first_name = clean_input(request.form.get('first_name', ''))
        last_name = clean_input(request.form.get('last_name', ''))
        
        if contact and first_name and last_name:
            user.contact = contact
            user.first_name = first_name
            user.last_name = last_name
            db.session.commit()
            flash('Profile updated successfully!', 'success')
            return redirect(url_for('dashboard.client_dashboard'))
        else:
            flash('Please provide valid details.', 'error')
            return redirect(url_for('dashboard.profile'))
            
    return render_template('profile.html', user=user)


@dashboard_bp.route('/admin/dashboard')
@login_required
@admin_required
def admin_dashboard():
    user = _get_current_user()
    from sqlalchemy import func

    total_users  = User.query.count()
    total_pets   = db.session.query(func.count(func.distinct(Booking.pet_name))).scalar() or 0
    today_appts  = Booking.query.filter_by(date=date.today()).count()

    current_month = date.today().month
    current_year  = date.today().year
    total_bookings_this_month = sum(
        1 for b in Booking.query.all()
        if b.date.month == current_month and b.date.year == current_year
    )

    staff_members = User.query.filter(User.role.in_(['staff', 'admin'])).all()

    return render_template('admin_dashboard.html',
                           user=user,
                           total_users=total_users,
                           total_pets=total_pets,
                           today_appointments=today_appts,
                           total_bookings_this_month=total_bookings_this_month,
                           staff_members=staff_members)


@dashboard_bp.route('/staff/dashboard')
@login_required
@staff_required
def staff_dashboard():
    user  = _get_current_user()
    today = date.today()

    today_appts    = Booking.query.filter_by(date=today).count()
    upcoming_appts = Booking.query.filter(Booking.date > today, Booking.status == 'confirmed').count()
    pending        = Booking.query.filter_by(status='pending').count()
    total_this_month = sum(
        1 for b in Booking.query.all()
        if b.date.month == today.month and b.date.year == today.year
    )

    bookings = Booking.query.order_by(Booking.date.asc(), Booking.slot.asc()).all()
    b_json = [{
        'id': b.id, 'date': b.date.isoformat(), 'slot': b.slot,
        'client_name': b.name, 'pet_name': b.pet_name, 'pet_type': b.pet_type,
        'service': b.service_ref.name, 'status': b.status
    } for b in bookings]

    return render_template('staff_dashboard.html',
                           user=user,
                           today_appointments=today_appts,
                           upcoming_appointments=upcoming_appts,
                           pending_bookings=pending,
                           total_patients_this_month=total_this_month,
                           bookings=bookings,
                           bookings_json=json.dumps(b_json))
