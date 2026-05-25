from flask import Blueprint, request, jsonify, current_app, session
from app.extensions import db
from app.models.notification import PushSubscription
from app.middleware.decorators import jwt_required, _get_current_user
from app.utils.validation import ValidationError, ensure_safe_text

api_push_bp = Blueprint('api_push', __name__)


@api_push_bp.route('/public-key', methods=['GET'])
def get_push_public_key():
    return jsonify({'public_key': current_app.config['VAPID_PUBLIC_KEY']}), 200


@api_push_bp.route('/subscribe', methods=['POST'])
def subscribe_push():
    user = _get_current_user()
    if not user:
        return jsonify({'error': 'Not authenticated'}), 401

    data = request.get_json()
    if not data or 'endpoint' not in data:
        return jsonify({'error': 'Invalid subscription data'}), 400

    try:
        endpoint = ensure_safe_text(data['endpoint'], field='endpoint', max_length=2048)
        p256dh = ensure_safe_text(data['keys']['p256dh'], field='p256dh', max_length=255)
        auth = ensure_safe_text(data['keys']['auth'], field='auth', max_length=255)
    except (KeyError, TypeError):
        return jsonify({'error': 'Invalid subscription data'}), 400
    except ValidationError as exc:
        return jsonify({'error': exc.message, 'field': exc.field}), exc.code

    existing = PushSubscription.query.filter_by(endpoint=endpoint).first()
    if existing:
        existing.user_id = user.id
        existing.p256dh  = p256dh
        existing.auth    = auth
    else:
        db.session.add(PushSubscription(
            user_id  = user.id,
            endpoint = endpoint,
            p256dh   = p256dh,
            auth     = auth
        ))

    # Save preference to user model
    user.push_enabled = True

    db.session.commit()
    return jsonify({'message': 'Subscribed successfully'}), 201


@api_push_bp.route('/unsubscribe', methods=['POST'])
def unsubscribe_push():
    user = _get_current_user()
    if not user:
        return jsonify({'error': 'Not authenticated'}), 401

    data = request.get_json()
    if not data or 'endpoint' not in data:
        return jsonify({'error': 'Invalid subscription data'}), 400

    try:
        endpoint = ensure_safe_text(data['endpoint'], field='endpoint', max_length=2048)
    except ValidationError as exc:
        return jsonify({'error': exc.message, 'field': exc.field}), exc.code

    existing = PushSubscription.query.filter_by(endpoint=endpoint).first()
    if existing:
        db.session.delete(existing)
        
    # Disable push for the user
    user.push_enabled = False
    
    db.session.commit()
    return jsonify({'message': 'Unsubscribed successfully'}), 200
