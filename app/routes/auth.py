import re
from flask import Blueprint, render_template, request, redirect, url_for, flash, session, jsonify
from app.extensions import db
from app.models.user import User
from app.middleware.decorators import _get_current_user
from app.services.auth_service import create_jwt_token
from app.services.rate_limiter import clear_attempts, is_limited, record_failure
from app.utils.sanitize import clean_input
from app.utils.logger import log_action

auth_bp = Blueprint('auth', __name__)
EMAIL_RE = re.compile(r'^[^@\s]+@[^@\s]+\.[^@\s]+$')


@auth_bp.route('/signup', methods=['GET', 'POST'])
def signup():
    if request.method == 'POST':
        fn  = clean_input(request.form.get('first_name', ''))
        ln  = clean_input(request.form.get('last_name', ''))
        em  = clean_input(request.form.get('email', '').lower())
        ct  = clean_input(request.form.get('contact', ''))
        pw  = request.form.get('password', '')
        pw2 = request.form.get('re_password', '')

        if not EMAIL_RE.match(em):
            flash('Please enter a valid email address.', 'error')
            return render_template('signup.html')

        if len(pw) < 8:
            flash('Password must be at least 8 characters.', 'error')
            return render_template('signup.html')

        if pw != pw2:
            flash('Passwords do not match.', 'error')
            return render_template('signup.html')

        if User.query.filter_by(email=em).first():
            flash('Email already registered.', 'error')
            return render_template('signup.html')

        # SECURITY IMPLEMENTATION: Privacy Notice or Consent
        # Mandates that users explicitly grant data privacy consent before 
        # registration and processing of personal data can proceed.
        consent_given = request.form.get('privacy_consent') == 'on'
        if not consent_given:
            flash('You must accept the Privacy Notice and Terms of Service to register.', 'error')
            return render_template('signup.html')
            
        # Check for successful OTP verification in the last 10 minutes
        from app.models.otp_verification import OtpVerification
        from datetime import datetime, timedelta
        
        ten_mins_ago = datetime.utcnow() - timedelta(minutes=10)
        otp_check = OtpVerification.query.filter(
            OtpVerification.email == em,
            OtpVerification.is_used == True,
            OtpVerification.created_at >= ten_mins_ago
        ).first()

        if not otp_check:
            flash('Email verification required.', 'error')
            return render_template('signup.html')

        # Create user
        user = User(
            first_name=fn,
            last_name=ln,
            email=em,
            contact=ct,
            privacy_consent=True,
            privacy_consent_at=datetime.utcnow()
        )
        # VETSYNC SECURITY MATRIX: Password Hashing Trigger
        # Captures the user's password input and triggers the Werkzeug cryptographically 
        # secure one-way hashing function before any database commit occurs.
        user.set_password(pw)
        db.session.add(user)
        db.session.commit()

        log_action('User Created', f'New account registered for {fn} {ln} ({em})', user=user)

        flash('Account created successfully! Please log in.', 'success')
        return redirect(url_for('auth.login'))

    return render_template('signup.html')




@auth_bp.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        if request.is_json:
            data = request.get_json()
        else:
            data = request.form

        email    = clean_input(data.get('email', '').lower())
        password = data.get('password', '')
        
        # DEBUG: Log the exact received inputs to identify any mismatches
        try:
            with open('scratch/login_debug.log', 'a', encoding='utf-8') as f:
                f.write(f"--- Login Attempt ---\n")
                f.write(f"Received email: {repr(email)}\n")
                f.write(f"Received password: {repr(password)}\n")
                dbg_user = User.query.filter_by(email=email).first()
                f.write(f"User found: {dbg_user is not None}\n")
                if dbg_user:
                    f.write(f"User active: {dbg_user.is_active}\n")
                    f.write(f"Password check: {dbg_user.check_password(password)}\n")
        except Exception as dbg_err:
            print(f"Debug logging failed: {dbg_err}")

        rate_key = _login_rate_key(email)

        if is_limited(rate_key):
            if request.is_json or request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                return jsonify({'error': 'Too many failed login attempts. Please try again later.'}), 429
            flash('Too many failed login attempts. Please try again later.', 'error')
            return render_template('login.html'), 429

        user     = User.query.filter_by(email=email).first()

        if user and user.check_password(password):
            if not user.is_active:
                if request.is_json or request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                    return jsonify({'error': 'Your account has been deactivated.'}), 403
                flash('Your account has been deactivated. Please contact support.', 'error')
                return render_template('login.html')

            # VETSYNC SECURITY MATRIX: Session Hijack & Cookie Protection
            # Clears the session to prevent session fixation attacks. Binds the user ID,
            # source IP address, and User-Agent signature directly into the cryptographically
            # encrypted session cookie. This allows the system to detect and drop mutated or
            # hijacked cookies at runtime.
            session.clear()
            session['user_id']   = user.id
            session['ip']        = request.remote_addr
            session['user_agent']= request.headers.get('User-Agent')
            session.permanent    = True
            clear_attempts(rate_key)
            log_action('Auth Success', f'Secure login established for {user.role}: {user.first_name} {user.last_name}', user=user)

            # VETSYNC SECURITY MATRIX: JWT Token Generation
            # Generates a highly secure, short-lived JSON Web Token (JWT) with encoded user identification
            # and RBAC credentials, enabling safe cross-origin client and PWA application accesses.
            access_token = create_jwt_token(user.id, user.role)

            next_url = request.args.get('next')
            if not next_url or not next_url.startswith('/'):
                if user.role == 'admin':
                    next_url = url_for('dashboard.admin_dashboard')
                elif user.role == 'staff':
                    next_url = url_for('dashboard.staff_dashboard')
                else:
                    next_url = url_for('main.index')

            if request.is_json or request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                return jsonify({
                    'success': True,
                    'access_token': access_token,
                    'redirect': next_url,
                    'role': user.role,
                    'user_name': user.first_name
                }), 200

            flash(f'Welcome back, {user.first_name}!', 'success')
            return redirect(next_url)
        else:
            if request.is_json or request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                record_failure(rate_key)
                return jsonify({'error': 'Invalid email or password.'}), 401
            record_failure(rate_key)
            flash('Invalid email or password.', 'error')
            return render_template('login.html')

    return render_template('login.html')


@auth_bp.route('/forgot-password')
def forgot_password():
    return render_template('forgot_password.html')


@auth_bp.route('/logout')
def logout():
    user = _get_current_user()
    if user:
        log_action('Logout', f'User session terminated: {user.first_name} {user.last_name}', user=user)
    session.clear()
    flash('Logged out successfully.', 'success')
    return redirect(url_for('main.index'))


def _login_rate_key(email):
    return f"login:{request.remote_addr or 'unknown'}:{email}"
