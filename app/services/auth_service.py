import jwt
from datetime import datetime
from flask import current_app
from flask_mail import Message
from app.extensions import mail




def create_jwt_token(user_id: int, role: str) -> str:
    payload = {
        'user_id': user_id,
        'role': role,
        'exp': datetime.utcnow() + current_app.config['JWT_ACCESS_TOKEN_EXPIRES']
    }
    return jwt.encode(payload, current_app.config['JWT_SECRET_KEY'], algorithm='HS256')


def decode_jwt_token(token: str):
    try:
        data = jwt.decode(token, current_app.config['JWT_SECRET_KEY'], algorithms=['HS256'])
        return data, 200
    except jwt.ExpiredSignatureError:
        return {'message': 'Token expired'}, 401
    except jwt.InvalidTokenError:
        return {'message': 'Invalid token'}, 401
