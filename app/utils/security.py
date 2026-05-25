import hmac
import os
# pyrefly: ignore [missing-import]
from flask import session, current_app, request, abort

# VETSYNC SECURITY MATRIX: Cross-Site Request Forgery (CSRF) Shield
# Generates a unique, cryptographically secure 32-byte session token for each user session.
# This token is injected into template forms and headers to prevent unauthorized cross-site requests.
def generate_csrf_token():
    """Generates a CSRF token for the current session if one doesn't exist."""
    if '_csrf_token' not in session:
        session['_csrf_token'] = os.urandom(32).hex()
    return session['_csrf_token']


# VETSYNC SECURITY MATRIX: Cross-Site Request Forgery (CSRF) Shield (Verification)
# Intercepts state-changing HTTP requests (POST, PUT, PATCH, DELETE) and validates
# the incoming 'csrf_token' (from forms) or 'X-CSRF-Token' header (for AJAX/PWA requests)
# against the cryptographically stored session token using constant-time comparison (hmac.compare_digest).
# This prevents timing attacks and completely blocks unauthorized cross-site state changes.
def verify_csrf_token():
    """Verifies the CSRF token in the request against the session token."""
    if request.method not in ["POST", "PUT", "PATCH", "DELETE"]:
        return

    if _csrf_exempt_request():
        return

    # Check both form field and header (for AJAX)
    token = request.form.get('csrf_token') or request.headers.get('X-CSRF-Token')
    
    provided_token = token if token else "MISSING"
    stored_token = session.get('_csrf_token')
    
    if not stored_token or not token or not hmac.compare_digest(stored_token, token):
        current_app.logger.warning(
            f"CSRF validation failed for IP: {request.remote_addr}. "
            f"Method: {request.method}, Path: {request.path}, "
            f"Provided Token: {provided_token[:10] if provided_token != 'MISSING' else 'MISSING'}, "
            f"Stored Token: {stored_token[:10] if stored_token else 'None'}"
        )
        # Extra debug for empty tokens
        if not token:
            current_app.logger.debug(f"Form data: {list(request.form.keys())}")
            current_app.logger.debug(f"Headers: {dict(request.headers)}")
        
        abort(403, description="CSRF validation failed. Request denied.")


def _csrf_exempt_request():
    # SECURITY: CSRF applies to browser session flows.
    # Bearer-authenticated API clients and stateless auth endpoints are exempt because
    # they do not rely on ambient browser cookies and would otherwise break REST usage.
    auth_header = request.headers.get('Authorization', '')
    if auth_header.startswith('Bearer '):
        return True

    if request.path.startswith('/api/v1/auth/'):
        return True

    if request.path == '/predict':
        return True

    return False

