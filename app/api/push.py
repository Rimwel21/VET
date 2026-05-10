from flask import Blueprint, request, jsonify, current_app
from app.extensions import db
from app.models.notification import PushSubscription
from app.middleware.decorators import jwt_required

api_push_bp = Blueprint('api_push', __name__)


@api_push_bp.route('/public-key', methods=['GET'])
def get_push_public_key():
    return jsonify({'public_key': current_app.config['VAPID_PUBLIC_KEY']}), 200


@api_push_bp.route('/subscribe', methods=['POST'])
@jwt_required
def subscribe_push(current_user_jwt):
    data = request.get_json()
    if not data or 'endpoint' not in data:
        return jsonify({'error': 'Invalid subscription data'}), 400

    existing = PushSubscription.query.filter_by(endpoint=data['endpoint']).first()
    if existing:
        existing.user_id = current_user_jwt.id
        existing.p256dh  = data['keys']['p256dh']
        existing.auth    = data['keys']['auth']
    else:
        db.session.add(PushSubscription(
            user_id  = current_user_jwt.id,
            endpoint = data['endpoint'],
            p256dh   = data['keys']['p256dh'],
            auth     = data['keys']['auth']
        ))

    db.session.commit()
    return jsonify({'message': 'Subscribed successfully'}), 201
