import base64
import json
from datetime import datetime
from flask import Blueprint, render_template, request, redirect, url_for, flash, jsonify, abort # type: ignore
from app.extensions import db
from app.models.contact import ContactMessage
from app.models.booking import Booking
from app.models.report import Report
from app.models.audit_log import AuditLog
from app.utils.logger import log_action
from app.models.availability import DoctorAvailability
from app.models.user import User
from app.middleware.decorators import login_required, admin_required, staff_required, _get_current_user
from app.services.push_service import send_push_notification
from app.services.email_service import send_booking_email

staff_bp = Blueprint('staff', __name__, url_prefix='/staff')


def _pet_key(booking):
    pet_name = (booking.pet_name or '').strip()
    email = (booking.email or '').strip().lower()
    return f"{pet_name}|{email}"


def _encode_pet_id(raw_key):
    return base64.urlsafe_b64encode(raw_key.encode('utf-8')).decode('ascii')


def _decode_pet_id(pet_id):
    return base64.urlsafe_b64decode(pet_id.encode('ascii')).decode('utf-8')


def _serialize_pet_record(record):
    return {
        'booking_id': record.id,
        'date': record.date.isoformat(),
        'service': record.service_ref.name if record.service_ref else 'Unknown service',
        'reason': record.visit_reason,
        'status': record.status,
        'notes': record.notes,
        'medical_history': record.medical_history,
        'handled_by': record.handled_by,
        'created_at': record.created_at.isoformat() if record.created_at else None,
    }


def _build_pet_directory(bookings):
    grouped = {}
    for booking in bookings:
        if not booking.pet_name or not booking.email:
            continue
        raw_key = _pet_key(booking)
        if raw_key not in grouped:
            grouped[raw_key] = {
                'pet_id': _encode_pet_id(raw_key),
                'name': booking.pet_name,
                'type': booking.pet_type,
                'breed': booking.pet_breed,
                'owner': booking.name,
                'email': booking.email,
                'latest_visit': booking.date.isoformat(),
            }

    return sorted(grouped.values(), key=lambda item: ((item['name'] or '').lower(), (item['owner'] or '').lower()))


@staff_bp.route('/appointments')
@login_required
@staff_required
def appointments():
    user     = _get_current_user()
    bookings = Booking.query.order_by(Booking.date.desc(), Booking.slot.desc()).all()
    return render_template('staff_appointments.html', user=user, bookings=bookings)


@staff_bp.route('/submitted-reports')
@login_required
@staff_required
def submitted_reports():
    user = _get_current_user()
    if user.role == 'admin':
        reports = Report.query.filter_by(is_deleted=False).order_by(Report.created_at.desc()).all()
    else:
        # Staff view rule: Only active reports
        reports = Report.query.filter_by(user_id=user.id, is_deleted=False).order_by(Report.created_at.desc()).all()
    return render_template('staff_submitted_reports.html', user=user, reports=reports)


@staff_bp.route("/reports/edit/<int:id>", methods=["POST"])
@login_required
@staff_required
def edit_report(id):
    user = _get_current_user()
    report = db.session.get(Report, id)
    if not report:
        from app.models.audit_log import AuditLog
        deleted_log = AuditLog.query.filter(
            AuditLog.action_type == 'Report Deleted',
            AuditLog.description.like(f"Deleted report ID {id}%")
        ).first()
        if deleted_log:
            if request.is_json or request.headers.get('Accept') == 'application/json':
                return jsonify({'error': 'This report has been deleted and is no longer available.'}), 410
            flash('This report has been deleted and is no longer available.', 'error')
            return redirect(url_for('staff.submitted_reports'))
        if request.is_json or request.headers.get('Accept') == 'application/json':
            return jsonify({'error': 'Report not found.'}), 404
        abort(404)

    if report.user_id != user.id:
        return jsonify({'error': 'Unauthorized'}), 403

    new_title = (request.form.get("title") or (request.json.get("title") if request.is_json else None)) or report.title
    new_desc = (request.form.get("content") or (request.json.get("content") if request.is_json else None)) or report.description

    if new_title != report.title or new_desc != report.description:
        # store previous version in history array
        history_entry = {
            "title": report.title,
            "content": report.description,
            "edited_at": datetime.utcnow().isoformat()
        }

        if not report.edit_history:
            report.edit_history = []
        
        hist = list(report.edit_history)
        hist.append(history_entry)
        report.edit_history = hist

        report.title = new_title
        report.description = new_desc

    # SECURITY IMPLEMENTATION: Transaction Isolation & Rollback
    # Wraps state changes in a transaction block to ensure that any database failure
    # cleanly rolls back the session, preventing partial commits and data corruption.
    try:
        db.session.commit()
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': 'Database transaction failed.'}), 500
    return redirect(url_for('staff.submitted_reports'))



@staff_bp.route('/offers')
@login_required
@staff_required
def offers():
    return redirect(url_for('staff.control_panel'))


@staff_bp.route('/control-panel')
@login_required
@staff_required
def control_panel():
    user = _get_current_user()
    bookings = Booking.query.order_by(Booking.date.asc(), Booking.slot.asc()).all()
    b_list = [{
        'id': b.id,
        'date': b.date.isoformat(),
        'slot': b.slot,
        'client_name': b.name,
        'pet_name': b.pet_name,
        'pet_type': b.pet_type,
        'service': b.service_ref.name if b.service_ref else 'Unknown',
        'status': b.status,
    } for b in bookings]
    clients = User.query.filter_by(role='client').order_by(User.first_name.asc()).all()
    inquiries = ContactMessage.query.order_by(ContactMessage.created_at.desc()).all()
    
    return render_template(
        'staff_control_panel.html',
        user=user,
        bookings_list=b_list,
        bookings_json=json.dumps(b_list),
        clients=clients,
        inquiries=inquiries
    )


@staff_bp.route('/send-custom-push', methods=['POST'])
@login_required
@staff_required
def send_custom_push():
    # SECURITY IMPLEMENTATION: Transaction Isolation & Rollback
    # Wraps the entire push notification dispatch in a try-except block.
    # This prevents any exception inside push_service from bubbling up to
    # the global error handler, ensuring the frontend always receives a
    # clean, structured JSON response instead of a masked 500 page.
    try:
        data = request.get_json(silent=True)
        if not data:
            return jsonify({'error': 'Invalid request body. Expected JSON.'}), 400

        user_id = data.get('user_id')
        title   = (data.get('title')   or '').strip()
        message = (data.get('message') or '').strip()

        if not user_id or not title or not message:
            return jsonify({'error': 'All fields (recipient, title, message) are required.'}), 400

        target = db.session.get(User, int(user_id))
        if not target or target.role != 'client':
            return jsonify({'error': 'Client not found.'}), 404

        # Precise diagnostics for user subscription state
        if not target.push_enabled:
            return jsonify({'error': 'Notification could not be sent — client has disabled notifications in their settings.'}), 422

        from app.models.notification import PushSubscription
        sub_exists = PushSubscription.query.filter_by(user_id=target.id).first()
        if not sub_exists:
            return jsonify({'error': 'Notification could not be sent — client subscription invalid or not registered in this browser.'}), 422

        sent = send_push_notification(int(user_id), title, message)
        if sent:
            return jsonify({'message': f'Notification sent successfully to {target.first_name} {target.last_name}.'}), 200
        else:
            return jsonify({'error': 'Notification could not be sent — client subscription invalid.'}), 422

    except ValueError:
        return jsonify({'error': 'Invalid user ID format.'}), 400
    except Exception as e:
        from flask import current_app
        current_app.logger.error(f'send_custom_push error: {e}')
        return jsonify({'error': f'Push notification failed: {str(e)}'}), 500


@staff_bp.route('/pet-records')
@login_required
@staff_required
def pet_records():
    user = _get_current_user()
    bookings = Booking.query.order_by(Booking.pet_name.asc(), Booking.date.desc()).all()
    pets = _build_pet_directory(bookings)
    return render_template('staff_pet_records.html', user=user, pets=pets)


@staff_bp.route('/pet-records/<pet_id>/history')
@login_required
@staff_required
def pet_history_detail(pet_id):
    try:
        raw_key = _decode_pet_id(pet_id)
    except Exception:
        return jsonify({'error': 'Invalid patient identifier.'}), 400

    pet_name, email = (raw_key.split('|', 1) + [''])[:2]
    if not pet_name or not email:
        return jsonify({'error': 'Invalid patient identifier.'}), 400

    records = (Booking.query
               .filter(Booking.pet_name == pet_name, Booking.email == email)
               .order_by(Booking.date.desc(), Booking.created_at.desc())
               .all())

    if not records:
        return jsonify({'error': 'Patient not found.'}), 404

    current = records[0]
    return jsonify({
        'pet_id': pet_id,
        'name': current.pet_name,
        'type': current.pet_type,
        'breed': current.pet_breed,
        'owner': current.name,
        'email': current.email,
        'history': [_serialize_pet_record(record) for record in records],
    })


@staff_bp.route('/audit-logs')
@login_required
@admin_required
def audit_logs():
    user = _get_current_user()
    logs = AuditLog.query.order_by(AuditLog.timestamp.desc()).limit(50).all()
    return render_template('admin_audit_logs.html', user=user, logs=logs)

@staff_bp.route('/api/audit-logs/data')
@login_required
@admin_required
def get_audit_logs_data():
    logs = AuditLog.query.order_by(AuditLog.timestamp.desc()).limit(100).all()
    return jsonify({
        'success': True,
        'logs': [log.to_dict() for log in logs]
    })


@staff_bp.route('/booking/<int:bid>/status', methods=['POST'])
@login_required
@staff_required
def update_booking_status(bid):
    status = request.form.get('status')
    if status not in ['confirmed', 'pending', 'cancelled', 'completed']:
        flash('Invalid status.', 'error')
        return redirect(request.referrer or url_for('dashboard.staff_dashboard'))

    booking = db.session.get(Booking, bid)
    if not booking:
        flash('Booking not found.', 'error')
    elif booking.status == status:
        flash(f'Booking #{bid} is already {status}.', 'info')
    else:
        booking.status = status
        user = _get_current_user()
        if user:
            booking.handled_by = f"{user.first_name} {user.last_name}"
        # SECURITY IMPLEMENTATION: Transaction Isolation & Rollback
        try:
            db.session.commit()
        except Exception as e:
            db.session.rollback()
            flash('Database transaction failed while updating booking.', 'error')
            return redirect(request.referrer or url_for('dashboard.staff_dashboard'))
        log_action('Booking Update', f'Changed status of Booking #{bid} to {status.capitalize()}.', user=user)

        if booking.user_id:
            send_push_notification(
                booking.user_id,
                f"Booking {status.capitalize()}",
                f"Your appointment for {booking.pet_name} ({booking.service_ref.name}) on {booking.date} is now {status}."
            )
        
        if status in ['confirmed', 'cancelled']:
            send_booking_email(booking, status)

        flash(f'Booking #{bid} updated to {status}.', 'success')

    return redirect(request.referrer or url_for('dashboard.staff_dashboard'))


@staff_bp.route('/booking/<int:bid>/cancel', methods=['POST'])
@login_required
@staff_required
def cancel_booking(bid):
    booking = db.session.get(Booking, bid)
    if not booking:
        flash('Booking not found.', 'error')
    else:
        booking.status = 'cancelled'
        user = _get_current_user()
        if user:
            booking.handled_by = f"{user.first_name} {user.last_name}"
        if booking.user_id:
            send_push_notification(
                booking.user_id,
                "Booking Cancelled",
                f"Your booking for {booking.pet_name} on {booking.date} has been cancelled by staff."
            )
        
        send_booking_email(booking, 'cancelled')
        # SECURITY IMPLEMENTATION: Transaction Isolation & Rollback
        try:
            db.session.commit()
        except Exception as e:
            db.session.rollback()
            flash('Database transaction failed while cancelling booking.', 'error')
            return redirect(request.referrer or url_for('dashboard.staff_dashboard'))
        flash(f'Booking #{bid} has been marked as cancelled.', 'success')

    return redirect(request.referrer or url_for('dashboard.staff_dashboard'))


@staff_bp.route('/booking/<int:bid>/delete', methods=['POST'])
@login_required
@staff_required
def delete_booking(bid):
    booking = db.session.get(Booking, bid)
    if not booking:
        flash('Booking not found.', 'error')
        return redirect(request.referrer or url_for('dashboard.staff_dashboard'))
    
    # Allow deletion only if cancelled or completed to prevent accidental removal of active appointments
    if booking.status not in ['cancelled', 'completed']:
        flash('Only cancelled or completed appointments can be permanently deleted.', 'error')
        return redirect(request.referrer or url_for('dashboard.staff_dashboard'))

    db.session.delete(booking)
    # SECURITY IMPLEMENTATION: Transaction Isolation & Rollback
    try:
        db.session.commit()
    except Exception as e:
        db.session.rollback()
        flash('Database transaction failed while deleting booking.', 'error')
        return redirect(request.referrer or url_for('dashboard.staff_dashboard'))
    flash(f'Booking #{bid} has been permanently removed.', 'success')
    return redirect(request.referrer or url_for('dashboard.staff_dashboard'))


@staff_bp.route('/availability', methods=['GET', 'POST'])
@login_required
@staff_required
def availability():
    if request.method == 'GET':
        blocks = DoctorAvailability.query.all()
        return jsonify([{'date': b.date.isoformat(), 'slot': b.slot, 'status': b.status} for b in blocks])

    data = request.get_json()
    target_date = data.get('date')
    slot        = data.get('slot')

    if not target_date or not slot:
        return jsonify({'error': 'Missing data'}), 400

    try:
        d = datetime.strptime(target_date, '%Y-%m-%d').date()
    except Exception:
        return jsonify({'error': 'Invalid date format'}), 400

    existing = DoctorAvailability.query.filter_by(date=d, slot=slot).first()
    if existing:
        db.session.delete(existing)
        status = 'available'
    else:
        db.session.add(DoctorAvailability(date=d, slot=slot, status='unavailable'))
        status = 'unavailable'

    # SECURITY IMPLEMENTATION: Transaction Isolation & Rollback
    try:
        db.session.commit()
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': 'Database transaction failed'}), 500
    return jsonify({'success': True, 'date': target_date, 'slot': slot, 'new_status': status})


@staff_bp.route('/inquiries')
@login_required
@staff_required
def inquiries():
    user = _get_current_user()
    messages = ContactMessage.query.order_by(ContactMessage.created_at.desc()).all()
    return render_template('staff_inquiries.html', user=user, messages=messages)


@staff_bp.route('/inquiries/delete/<int:mid>', methods=['POST'])
@login_required
@staff_required
def delete_inquiry(mid):
    msg = db.session.get(ContactMessage, mid)
    if msg:
        db.session.delete(msg)
        # SECURITY IMPLEMENTATION: Transaction Isolation & Rollback
        try:
            db.session.commit()
        except Exception as e:
            db.session.rollback()
            flash('Database transaction failed.', 'error')
        flash('Inquiry removed.', 'success')
    return redirect(url_for('staff.inquiries'))
