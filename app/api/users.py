from flask import Blueprint, request, jsonify
from app.extensions import db
from app.models.user import User
from app.middleware.decorators import role_required
from app.utils.logger import log_action

api_users_bp = Blueprint('api_users', __name__)

PROTECTED_ADMIN_EMAIL = 'adminvetclinic@gmail.com'


@api_users_bp.route('', methods=['GET', 'POST'])
@role_required(['admin'])
def manage_users(current_user_jwt):
    if request.method == 'GET':
        # Only return staff accounts (not admin, not client)
        users = User.query.filter_by(role='staff').all()
        return jsonify([{
            'id': u.id, 'first_name': u.first_name, 'last_name': u.last_name,
            'email': u.email, 'role': u.role, 'contact': u.contact, 'is_active': u.is_active
        } for u in users]), 200

    data = request.get_json()
    em   = data.get('email', '').strip().lower()

    # Block creation of admin accounts via API
    requested_role = data.get('role', 'staff')
    if requested_role == 'admin':
        return jsonify({'error': 'Creation of admin accounts is not permitted.'}), 403

    # Only allow staff role
    if requested_role not in ('staff',):
        requested_role = 'staff'

    if User.query.filter_by(email=em).first():
        return jsonify({'error': 'Email already exists'}), 409

    new_user = User(
        first_name=data.get('first_name', ''),
        last_name=data.get('last_name', ''),
        email=em,
        contact=data.get('contact', ''),
        role='staff'
    )
    new_user.set_password(data.get('password', 'default123'))
    db.session.add(new_user)
    db.session.commit()
    log_action('Staff Created', f"New staff account created: {new_user.first_name} {new_user.last_name} ({em})", user=current_user_jwt)
    return jsonify({'message': 'Staff account created successfully', 'user_id': new_user.id}), 201


@api_users_bp.route('/<int:user_id>', methods=['GET', 'PUT', 'DELETE'])
@role_required(['admin'])
def manage_single_user(current_user_jwt, user_id):
    user = db.session.get(User, user_id)
    if not user:
        return jsonify({'message': 'User not found'}), 404

    # Protect admin account from modification/deletion via this endpoint
    if user.role == 'admin' or user.email == PROTECTED_ADMIN_EMAIL:
        if request.method == 'DELETE':
            return jsonify({'error': 'The admin account cannot be deleted.'}), 403

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

        # Prevent role escalation to admin
        new_role = data.get('role', user.role)
        if new_role == 'admin':
            new_role = 'staff'
        user.role = new_role

        if 'is_active' in data:
            user.is_active = data['is_active']
        if data.get('password'):
            user.set_password(data['password'])
        db.session.commit()
        return jsonify({'message': 'Staff account updated successfully'}), 200

    # DELETE — hard delete staff account
    name = f"{user.first_name} {user.last_name}"
    log_action('Staff Deleted', f"Staff account permanently removed: {name} ({user.email})", user=current_user_jwt)
    db.session.delete(user)
    db.session.commit()
    return jsonify({'message': 'Staff account deleted successfully'}), 200


@api_users_bp.route('/<int:user_id>/deactivate', methods=['POST'])
@role_required(['admin'])
def deactivate_user(current_user_jwt, user_id):
    user = db.session.get(User, user_id)
    if not user:
        return jsonify({'error': 'User not found'}), 404
    if user.role == 'admin' or user.email == PROTECTED_ADMIN_EMAIL:
        return jsonify({'error': 'The admin account cannot be deactivated.'}), 403
    if not user.is_active:
        return jsonify({'error': 'Staff account is already deactivated.'}), 409

    user.is_active = False
    db.session.commit()
    log_action('Staff Deactivated', f"Staff account deactivated: {user.first_name} {user.last_name} ({user.email})", user=current_user_jwt)
    return jsonify({'message': f'Staff account for {user.first_name} {user.last_name} has been deactivated successfully.'}), 200


@api_users_bp.route('/<int:user_id>/reactivate', methods=['POST'])
@role_required(['admin'])
def reactivate_user(current_user_jwt, user_id):
    user = db.session.get(User, user_id)
    if not user:
        return jsonify({'error': 'User not found'}), 404
    if user.is_active:
        return jsonify({'error': 'Staff account is already active.'}), 409

    user.is_active = True
    db.session.commit()
    log_action('Staff Reactivated', f"Staff account reactivated: {user.first_name} {user.last_name} ({user.email})", user=current_user_jwt)
    return jsonify({'message': f'Staff account for {user.first_name} {user.last_name} has been reactivated successfully.'}), 200
