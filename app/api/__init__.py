from flask import Blueprint
from app.api.auth import api_auth_bp
from app.api.appointments import api_appointments_bp
from app.api.users import api_users_bp
from app.api.notifications import api_notifications_bp
from app.api.availability import api_availability_bp
from app.api.push import api_push_bp
from app.api.reports import api_reports_bp
from app.api.chatbot import api_chatbot_bp

# Parent blueprint — all children inherit /api/v1 prefix
api_v1 = Blueprint('api_v1', __name__, url_prefix='/api/v1')


def register_api(app):
    api_v1.register_blueprint(api_auth_bp,          url_prefix='/auth')
    api_v1.register_blueprint(api_appointments_bp,  url_prefix='/appointments')
    api_v1.register_blueprint(api_users_bp,          url_prefix='/users')
    api_v1.register_blueprint(api_notifications_bp, url_prefix='/notifications')
    api_v1.register_blueprint(api_availability_bp,  url_prefix='/schedule')
    api_v1.register_blueprint(api_push_bp,           url_prefix='/push')
    api_v1.register_blueprint(api_reports_bp,        url_prefix='/reports')
    api_v1.register_blueprint(api_chatbot_bp,        url_prefix='/chatbot')
    app.register_blueprint(api_v1)
