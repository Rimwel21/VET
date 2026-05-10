from functools import wraps
from flask import session, request, redirect, url_for, flash, jsonify
from app.extensions import db
from app.services.auth_service import decode_jwt_token


def _get_current_user():
    from app.models.user import User
    uid = session.get('user_id')
    return db.session.get(User, uid) if uid else None


def login_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        if not _get_current_user():
            flash('Please log in to access that page.', 'error')
            return redirect(url_for('auth.login', next=request.url))
        return f(*args, **kwargs)
    return decorated


def admin_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        user = _get_current_user()
        if not user or user.role != 'admin':
            flash('Access denied: Admins only.', 'error')
            return redirect(url_for('main.index'))
        return f(*args, **kwargs)
    return decorated


def staff_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        user = _get_current_user()
        if not user or user.role != 'staff':
            flash('Access denied: Staff only.', 'error')
            return redirect(url_for('main.index'))
        return f(*args, **kwargs)
    return decorated


def jwt_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        from app.models.user import User
        token = _extract_bearer_token()
        if not token:
            return jsonify({'message': 'Token is missing!'}), 401

        decoded, status = decode_jwt_token(token)
        if status != 200:
            return jsonify(decoded), status

        user = db.session.get(User, decoded['user_id'])
        if not user:
            return jsonify({'message': 'User not found'}), 401

        return f(user, *args, **kwargs)
    return decorated


def role_required(roles):
    def decorator(f):
        @wraps(f)
        def decorated(*args, **kwargs):
            from app.models.user import User
            token = _extract_bearer_token()
            if not token:
                user = _get_current_user()
                if not user:
                    return jsonify({'message': 'Token is missing!'}), 401
                if user.role not in roles:
                    return jsonify({'message': 'Access denied: Insufficient role'}), 403
                return f(user, *args, **kwargs)

            decoded, status = decode_jwt_token(token)
            if status != 200:
                return jsonify(decoded), status

            user = db.session.get(User, decoded['user_id'])
            if not user:
                return jsonify({'message': 'User not found'}), 401

            if user.role not in roles:
                return jsonify({'message': 'Access denied: Insufficient role'}), 403

            return f(user, *args, **kwargs)
        return decorated
    return decorator


def _extract_bearer_token():
    auth_header = request.headers.get('Authorization', '')
    parts = auth_header.split()
    if len(parts) == 2 and parts[0] == 'Bearer':
        return parts[1]
    return None
