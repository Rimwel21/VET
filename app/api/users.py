from flask import Blueprint, request, jsonify
from app.extensions import db
from app.models.user import User
from app.middleware.decorators import role_required

api_users_bp = Blueprint('api_users', __name__)


@api_users_bp.route('', methods=['GET', 'POST'])
@role_required(['admin'])
def manage_users(current_user_jwt):
    if request.method == 'GET':
        users = User.query.all()
        return jsonify([{
            'id': u.id, 'first_name': u.first_name, 'last_name': u.last_name,
            'email': u.email, 'role': u.role, 'contact': u.contact, 'is_active': u.is_active
        } for u in users]), 200

    data = request.get_json()
    em   = data['email'].strip().lower()
    if User.query.filter_by(email=em).first():
        return jsonify({'error': 'Email already exists'}), 409

    new_user = User(
        first_name=data.get('first_name', ''),
        last_name=data.get('last_name', ''),
        email=em,
        contact=data.get('contact', ''),
        role=data.get('role', 'client')
    )
    new_user.set_password(data.get('password', 'default123'))
    db.session.add(new_user)
    db.session.commit()
    return jsonify({'message': 'User created successfully', 'user_id': new_user.id}), 201


@api_users_bp.route('/<int:user_id>', methods=['GET', 'PUT', 'DELETE'])
@role_required(['admin'])
def manage_single_user(current_user_jwt, user_id):
    user = db.session.get(User, user_id)
    if not user:
        return jsonify({'message': 'User not found'}), 404

    if request.method == 'GET':
        return jsonify({
            'id': user.id, 'first_name': user.first_name, 'last_name': user.last_name,
            'email': user.email, 'role': user.role, 'contact': user.contact, 'is_active': user.is_active
        }), 200

    if request.method == 'PUT':
        data = request.get_json()
        user.first_name = data.get('first_name', user.first_name)
        user.last_name  = data.get('last_name',  user.last_name)
        user.email      = data.get('email',       user.email).strip().lower()
        user.contact    = data.get('contact',     user.contact)
        user.role       = data.get('role',        user.role)
        if 'is_active' in data:
            user.is_active = data['is_active']
        if data.get('password'):
            user.set_password(data['password'])
        db.session.commit()
        return jsonify({'message': 'User updated successfully'}), 200

    # DELETE
    db.session.delete(user)
    db.session.commit()
    return jsonify({'message': 'User deleted successfully'}), 200
