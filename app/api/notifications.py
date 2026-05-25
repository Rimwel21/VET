from flask import Blueprint, request, jsonify
from app.extensions import db
from app.models.user import User
from app.models.notification import Notification
from app.middleware.decorators import jwt_required
from app.services.push_service import send_push_notification
from app.utils.validation import FieldSpec, ValidationError, validate_fields

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

    data = request.get_json() or {}
    try:
        payload = validate_fields(data, {
            'title': FieldSpec(required=True, max_length=100),
            'message': FieldSpec(required=True, max_length=2000, allow_newlines=True),
        })
    except ValidationError as exc:
        return jsonify({'error': exc.message, 'field': exc.field}), exc.code

    title = payload['title']
    message = payload['message']
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
    send_push_notification(uid, title, message, persist=False)
    return jsonify({'message': 'Notification sent successfully', 'notification_id': note.id}), 201
