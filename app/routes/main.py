from datetime import date
from flask import Blueprint, render_template, request, redirect, url_for, flash, send_from_directory, current_app
from app.extensions import db
from app.models.service import Service
from app.models.contact import ContactMessage
from app.services.booking_service import PET_TYPES

main_bp = Blueprint('main', __name__)


@main_bp.route('/')
def index():
    services = Service.query.all()
    today = date.today().isoformat()
    return render_template('index.html', services=services, pet_types=PET_TYPES, today=today)


@main_bp.route('/about')
def about():
    return render_template('about.html')


@main_bp.route('/services')
def services_page():
    return render_template('services.html', services=Service.query.all())


@main_bp.route('/contact', methods=['GET', 'POST'])
def contact():
    if request.method == 'POST':
        n = request.form.get('name', '').strip()
        e = request.form.get('email', '').strip()
        s = request.form.get('subject', '').strip()
        m = request.form.get('message', '').strip()

        if not all([n, e, m]):
            flash('Please fill in all required fields.', 'error')
            return render_template('contact.html')

        db.session.add(ContactMessage(name=n, email=e, subject=s, message=m))
        db.session.commit()
        flash('Message sent! We will get back to you shortly.', 'success')
        return redirect(url_for('main.contact'))

    return render_template('contact.html')


@main_bp.route('/offline')
def offline_page():
    return render_template('offline.html')


@main_bp.route('/service-worker.js')
def service_worker():
    response = send_from_directory(current_app.static_folder, 'service-worker.js')
    response.headers['Service-Worker-Allowed'] = '/'
    response.headers['Cache-Control'] = 'no-cache'
    return response


@main_bp.route('/favicon.ico')
def favicon():
    return send_from_directory(
        f'{current_app.static_folder}/images',
        'pwa-icon-192.png',
        mimetype='image/png'
    )
