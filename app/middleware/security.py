from flask import session, request, redirect, url_for, flash


def register_security_hooks(app):
    """Registers before/after request security hooks on the app."""

    @app.before_request
    def verify_request_safety():
        from app.utils.security import verify_csrf_token
        
        # 1. CSRF Protection (Global Enforcement)
        verify_csrf_token()

        # 2. HTTPS Enforcement
        if _https_required(app) and not _request_is_secure():
            return redirect(request.url.replace('http://', 'https://', 1), code=301)

        """
        Session Hijacking Protection (DISABLED FOR MOBILE COMPATIBILITY):
        Previously locked the session to the user's IP and User-Agent.
        This was causing frequent logouts on mobile due to UA/IP transitions.
        """
        # if 'user_id' in session:
        #     if (session.get('ip') != request.remote_addr or
        #             session.get('user_agent') != request.headers.get('User-Agent')):
        #         session.clear()
        #         flash('Security Alert: Session terminated due to suspicious activity.', 'error')
        #         return redirect(url_for('auth.login'))

    @app.after_request
    def add_security_headers(response):
        """Adds production-grade security headers to every response."""
        response.headers['X-Content-Type-Options'] = 'nosniff'
        response.headers['X-Frame-Options'] = 'SAMEORIGIN'
        response.headers['X-XSS-Protection'] = '1; mode=block'
        response.headers['Referrer-Policy'] = 'strict-origin-when-cross-origin'
        response.headers['Permissions-Policy'] = 'camera=(), microphone=(), geolocation=()'
        if _https_required(app):
            response.headers['Strict-Transport-Security'] = 'max-age=31536000; includeSubDomains'
        response.headers['Content-Security-Policy'] = (
            "default-src 'self'; "
            "script-src 'self' 'unsafe-inline' https://cdn.jsdelivr.net https://cdnjs.cloudflare.com; "
            "style-src 'self' 'unsafe-inline' https://fonts.googleapis.com; "
            "font-src 'self' https://fonts.gstatic.com; "
            "img-src 'self' data:; "
            "connect-src 'self';"
        )
        return response


def _https_required(app):
    return bool(app.config.get('ENFORCE_HTTPS'))


def _request_is_secure():
    return request.is_secure or request.headers.get('X-Forwarded-Proto', '').lower() == 'https'
