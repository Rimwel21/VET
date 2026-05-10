import re
from flask import Blueprint, request, jsonify, current_app
from app.models.user import User
from app.services.auth_service import create_jwt_token
from app.services.otp_service import (
    create_otp, verify_otp_code, send_otp_email, 
    verify_reset_otp, reset_password_with_token
)
from app.services.rate_limiter import clear_attempts, is_limited, record_failure
from app.utils.sanitize import clean_input

api_auth_bp = Blueprint('api_auth', __name__)
EMAIL_RE = re.compile(r'^[^@\s]+@[^@\s]+\.[^@\s]+$')


@api_auth_bp.route('/login', methods=['POST'])
def api_login():
    data     = request.get_json(silent=True) or {}
    email    = clean_input(data.get('email', '').strip().lower())
    password = data.get('password', '')
    rate_key = _login_rate_key(email)

    if is_limited(rate_key):
        return jsonify({'message': 'Too many failed login attempts. Please try again later.'}), 429

    user = User.query.filter_by(email=email).first()
    if user and user.check_password(password):
        if not user.is_active:
            return jsonify({'message': 'Account deactivated'}), 401
        clear_attempts(rate_key)
        token = create_jwt_token(user.id, user.role)
        return jsonify(access_token=token, user_id=user.id, role=user.role), 200

    record_failure(rate_key)
    return jsonify({'message': 'Invalid credentials'}), 401


@api_auth_bp.route('/send-otp', methods=['POST'])
def send_otp_endpoint():
    data = request.get_json() or {}
    email = clean_input(data.get('email', '').strip().lower())
    
    if not email or not EMAIL_RE.match(email):
        return jsonify({'message': 'A valid email is required'}), 400
    
    raw_otp, error = create_otp(email)
    if error:
        return jsonify({'message': error}), 429 if "Rate limit" in error else 400
        
    if send_otp_email(email, raw_otp):
        return jsonify({'message': 'OTP sent successfully'}), 200

    if current_app.debug:
        return jsonify({
            'message': 'Email delivery is unavailable in this local environment. Use the displayed OTP to continue.',
            'dev_otp': raw_otp
        }), 200

    return jsonify({'message': 'Failed to send email'}), 500


@api_auth_bp.route('/verify-otp', methods=['POST'])
def verify_otp_endpoint():
    data = request.get_json() or {}
    email = clean_input(data.get('email', '').strip().lower())
    otp = data.get('otp', '').strip()
    
    if not email or not otp:
        return jsonify({'message': 'Email and OTP are required'}), 400
        
    success, message = verify_otp_code(email, otp)
    if success:
        return jsonify({'verified': True, 'message': message}), 200
    else:
        return jsonify({'verified': False, 'message': message}), 400


@api_auth_bp.route('/forgot-password', methods=['POST'])
def forgot_password_endpoint():
    data = request.get_json() or {}
    email = clean_input(data.get('email', '').strip().lower())
    
    if not email:
        return jsonify({'message': 'Email is required'}), 400
    
    # Check if user exists (Email enumeration protection)
    user = User.query.filter_by(email=email).first()
    
    if user:
        raw_otp, error = create_otp(email, user_id=user.id)
        if not error:
            send_otp_email(email, raw_otp)
            
    # Always return success message for security
    return jsonify({'message': 'If this email is registered, an OTP has been sent.'}), 200


@api_auth_bp.route('/verify-reset-otp', methods=['POST'])
def verify_reset_otp_endpoint():
    data = request.get_json() or {}
    email = clean_input(data.get('email', '').strip().lower())
    otp = data.get('otp', '').strip()
    
    if not email or not otp:
        return jsonify({'message': 'Email and OTP are required'}), 400
        
    token, message = verify_reset_otp(email, otp)
    if token:
        return jsonify({'verified': True, 'reset_token': token}), 200
    else:
        return jsonify({'verified': False, 'message': message}), 400


@api_auth_bp.route('/reset-password', methods=['POST'])
def reset_password_endpoint():
    data = request.get_json() or {}
    email = clean_input(data.get('email', '').strip().lower())
    token = data.get('token', '').strip()
    new_password = data.get('new_password', '')
    confirm_password = data.get('confirm_password', '')
    
    if not email or not token or not new_password:
        return jsonify({'message': 'All fields are required'}), 400
        
    if new_password != confirm_password:
        return jsonify({'message': 'Passwords do not match'}), 400
        
    if len(new_password) < 8:
        return jsonify({'message': 'Password must be at least 8 characters'}), 400
        
    success, message = reset_password_with_token(email, token, new_password)
    if success:
        return jsonify({'message': message}), 200
    else:
        return jsonify({'message': message}), 400


def _login_rate_key(email):
    return f"login:{request.remote_addr or 'unknown'}:{email}"
