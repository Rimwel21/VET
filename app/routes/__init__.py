from app.routes.main import main_bp
from app.routes.auth import auth_bp
from app.routes.booking import booking_bp
from app.routes.dashboard import dashboard_bp
from app.routes.staff import staff_bp
from app.routes.vetscan import vetscan_bp


def register_blueprints(app):
    app.register_blueprint(main_bp)
    app.register_blueprint(auth_bp)
    app.register_blueprint(booking_bp)
    app.register_blueprint(dashboard_bp)
    app.register_blueprint(staff_bp)
    app.register_blueprint(vetscan_bp)
