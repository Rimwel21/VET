import secrets
from datetime import datetime, timedelta
from werkzeug.security import generate_password_hash, check_password_hash
from flask import current_app
from flask_mail import Message
from app.extensions import db, mail
from app.models.otp_verification import OtpVerification

def generate_secure_otp() -> str:
    """Generate a secure 6-digit numeric OTP."""
    return "".join(secrets.choice("0123456789") for _ in range(6))

def create_otp(email: str, user_id: int = None):
    """
    Generate, hash, and store a new OTP.
    Includes rate limiting: max 3 requests per minute per email.
    """
    # Rate limit check
    one_minute_ago = datetime.utcnow() - timedelta(minutes=1)
    recent_requests = OtpVerification.query.filter(
        OtpVerification.email == email,
        OtpVerification.created_at >= one_minute_ago
    ).count()

    if recent_requests >= 3:
        return None, "Rate limit exceeded. Please wait a minute."

    raw_otp = generate_secure_otp()
    hashed_otp = generate_password_hash(raw_otp)
    
    expires_at = datetime.utcnow() + timedelta(minutes=5)
    
    otp_entry = OtpVerification(
        email=email,
        user_id=user_id,
        otp_code=hashed_otp,
        expires_at=expires_at
    )
    
    db.session.add(otp_entry)
    db.session.commit()
    
    return raw_otp, None

def verify_otp_code(email: str, raw_otp: str):
    """
    Verify the provided OTP for the given email.
    Checks for expiration, usage, and brute force attempts.
    """
    otp_record = OtpVerification.query.filter_by(email=email).order_by(OtpVerification.created_at.desc()).first()

    if not otp_record:
        return False, "No OTP request found for this email."

    if otp_record.is_used:
        return False, "This OTP has already been used."

    if otp_record.is_expired():
        return False, "This OTP has expired."

    if otp_record.attempts >= 5:
        return False, "Maximum attempts reached. Please request a new OTP."

    if check_password_hash(otp_record.otp_code, raw_otp):
        otp_record.is_used = True
        db.session.commit()
        return True, "Verification successful."
    else:
        otp_record.attempts += 1
        db.session.commit()
        remaining = 5 - otp_record.attempts
        return False, f"Invalid OTP. {remaining} attempts remaining."

def verify_reset_otp(email: str, raw_otp: str):
    """
    Verify OTP for password reset and issue a short-lived reset token.
    """
    success, message = verify_otp_code(email, raw_otp)
    if not success:
        return None, message
    
    # Generate a secure reset token
    token = secrets.token_urlsafe(32)
    
    # Find the record we just verified (it's marked as used now)
    otp_record = OtpVerification.query.filter_by(
        email=email, 
        is_used=True
    ).order_by(OtpVerification.created_at.desc()).first()
    
    if otp_record:
        otp_record.reset_token = token
        otp_record.token_expires_at = datetime.utcnow() + timedelta(minutes=5)
        db.session.commit()
        
    return token, "OTP verified. You can now reset your password."

def reset_password_with_token(email: str, token: str, new_password: str):
    """
    Finalize password reset using the issued token.
    """
    from app.models.user import User
    
    otp_record = OtpVerification.query.filter_by(
        email=email,
        reset_token=token
    ).first()
    
    if not otp_record:
        return False, "Invalid reset token."
        
    if datetime.utcnow() > otp_record.token_expires_at:
        return False, "Reset token has expired."
        
    user = User.query.filter_by(email=email).first()
    if not user:
        return False, "User not found."
        
    # Update password
    user.set_password(new_password)
    
    # Invalidate token
    otp_record.reset_token = None
    otp_record.token_expires_at = None
    
    db.session.commit()
    return True, "Password reset successfully."

def send_otp_email(email: str, otp: str):
    """Send the OTP via email using Flask-Mail."""
    msg = Message(
        subject="VetCare Pro Verification Code",
        sender=current_app.config.get('MAIL_USERNAME'),
        recipients=[email]
    )
    msg.body = f"Your OTP code is: {otp}\nThis code will expire in 5 minutes."
    try:
        mail.send(msg)
        return True
    except Exception as e:
        current_app.logger.error(f"Failed to send email: {e}")
        return False
