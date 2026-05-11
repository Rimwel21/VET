from flask import Blueprint, request, jsonify, current_app, session
from app.extensions import db
from app.models.notification import PushSubscription
from app.middleware.decorators import jwt_required, _get_current_user

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

    existing = PushSubscription.query.filter_by(endpoint=data['endpoint']).first()
    if existing:
        existing.user_id = user.id
        existing.p256dh  = data['keys']['p256dh']
        existing.auth    = data['keys']['auth']
    else:
        db.session.add(PushSubscription(
            user_id  = user.id,
            endpoint = data['endpoint'],
            p256dh   = data['keys']['p256dh'],
            auth     = data['keys']['auth']
        ))

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

    existing = PushSubscription.query.filter_by(endpoint=data['endpoint']).first()
    if existing:
        db.session.delete(existing)
        db.session.commit()
        return jsonify({'message': 'Unsubscribed successfully'}), 200

    return jsonify({'message': 'No subscription found'}), 200
