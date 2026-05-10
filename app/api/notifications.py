from flask import Blueprint, request, jsonify
from app.extensions import db
from app.models.user import User
from app.models.notification import Notification
from app.middleware.decorators import jwt_required
from app.services.push_service import send_push_notification

api_notifications_bp = Blueprint('api_notifications', __name__)


@api_notifications_bp.route('', methods=['GET', 'POST'])
@jwt_required
def notifications(current_user_jwt):
    if request.method == 'GET':
        items = (Notification.query
                 .filter_by(user_id=current_user_jwt.id)
                 .order_by(Notification.created_at.desc())
                 .all())
        return jsonify([{
            'id': n.id, 'title': n.title, 'message': n.message,
            'read': n.read, 'created_at': n.created_at.isoformat()
        } for n in items]), 200

    data    = request.get_json()
    title   = data.get('title')
    message = data.get('message')
    if not title or not message:
        return jsonify({'error': 'Title and message are required'}), 400

    target_user_id = data.get('user_id')
    if target_user_id and current_user_jwt.role == 'admin':
        if not db.session.get(User, target_user_id):
            return jsonify({'error': 'Target user not found'}), 404
        uid = target_user_id
    else:
        uid = current_user_jwt.id

    note = Notification(user_id=uid, title=title, message=message)
    db.session.add(note)
    db.session.commit()
    send_push_notification(uid, title, message)
    return jsonify({'message': 'Notification sent successfully', 'notification_id': note.id}), 201
