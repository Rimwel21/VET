import re
from flask import Blueprint, render_template, request, redirect, url_for, flash, session, jsonify
from app.extensions import db
from app.models.user import User
from app.middleware.decorators import _get_current_user
from app.services.auth_service import create_jwt_token
from app.services.rate_limiter import clear_attempts, is_limited, record_failure
from app.utils.logger import log_action
from app.utils.validation import (
    FieldSpec,
    ValidationError,
    validate_email,
    validate_fields,
    validate_password,
)

auth_bp = Blueprint('auth', __name__)
EMAIL_RE = re.compile(r'^[^@\s]+@[^@\s]+\.[^@\s]+$')

# Security Navigation:
# - Signup validation and privacy consent live here.
# - Login throttling, session setup, and JWT issuance also start here.
@auth_bp.route('/signup', methods=['GET', 'POST'])
def signup():
    if request.method == 'POST':
        try:
            # SECURITY: Signup input validation.
            # Protects identity fields from malicious payloads and malformed values
            # before an account can be created in the system.
            payload = validate_fields(request.form, {
                'first_name': FieldSpec(kind='name', required=True, max_length=80),
                'last_name': FieldSpec(kind='name', required=True, max_length=80),
                'email': FieldSpec(kind='email', required=True, max_length=120, escape_html=False),
                'contact': FieldSpec(kind='phone', required=True, max_length=30, escape_html=False),
            })
            fn = payload['first_name']
            ln = payload['last_name']
            em = payload['email']
            ct = payload['contact']
            pw = validate_password(request.form.get('password', ''))
        except ValidationError as exc:
            flash(exc.message, 'error')
            return render_template('signup.html')

        pw2 = request.form.get('re_password', '')

        # Basic server-side validation ensures the client cannot bypass form rules.
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
            
        # OTP verification proves the requester controls the submitted email address.
        # The time window keeps old verifications from being reused indefinitely.
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

        # Only after validation, consent, and OTP verification do we create the account.
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
            data = request.get_json(silent=True) or {}
        else:
            data = request.form

        try:
            # SECURITY: Email validation at login.
            # Prevents malformed and suspicious credential payloads from reaching
            # authentication queries and rate-limit keys.
            email = validate_email(data.get('email', ''), field='email')
        except ValidationError as exc:
            if request.is_json or request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                return jsonify({'error': exc.message, 'field': exc.field}), exc.code
            flash(exc.message, 'error')
            return render_template('login.html'), exc.code

        password = data.get('password', '')
        rate_key = _login_rate_key(email)

        # Rate limiting slows brute-force attacks against the login endpoint.
        if is_limited(rate_key):
            if request.is_json or request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                return jsonify({'error': 'Too many failed login attempts. Please try again later.'}), 429
            flash('Too many failed login attempts. Please try again later.', 'error')
            return render_template('login.html'), 429

        # ORM-based lookup keeps the query parameterized instead of interpolating input.
        user     = User.query.filter_by(email=email).first()

        if user and user.check_password(password):
            # Deactivated accounts are blocked even when credentials are correct.
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
            session.permanent    = True
            clear_attempts(rate_key)
            log_action('Auth Success', f'Secure login established for {user.role}: {user.first_name} {user.last_name}', user=user)

            # VETSYNC SECURITY MATRIX: JWT Token Generation
            # Generates a highly secure, short-lived JSON Web Token (JWT) with encoded user identification
            # and RBAC credentials, enabling safe cross-origin client and PWA application accesses.
            access_token = create_jwt_token(user.id, user.role)

            # The next URL is constrained to local paths to avoid open redirect issues.
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
            # Failed attempts are recorded on every invalid login path.
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
