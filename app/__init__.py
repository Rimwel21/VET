from flask import session # type: ignore
from app.extensions import db, mail, migrate
from app.middleware.security import register_security_hooks
from app.routes import register_blueprints
from app.api import register_api
from config import config


def create_app(config_name='default'):
    from flask import Flask # type: ignore
    app = Flask(__name__, template_folder='templates')
    app.config.from_object(config[config_name])

    # Init extensions
    db.init_app(app)
    migrate.init_app(app, db)
    mail.init_app(app)

    # Register security hooks (before/after request)
    register_security_hooks(app)

    # Register all route blueprints
    register_blueprints(app)

    # Register all API blueprints
    register_api(app)

    # Context processor — injects current_user and csrf_token into every template
    @app.context_processor
    def inject_globals():
        from app.models.user import User
        from app.utils.security import generate_csrf_token
        uid = session.get('user_id')
        current_user = db.session.get(User, uid) if uid else None
        return dict(current_user=current_user, csrf_token=generate_csrf_token)

    # Local bootstrap guard. Production deployments should use Flask-Migrate.
    if app.config.get('AUTO_CREATE_DB'):
        with app.app_context():
            db.create_all()
            _run_migrations()
            _seed_data()
    return app


def _run_migrations():
    """Applies simple schema migrations that may be missing in older DBs."""
    # pyrefly: ignore [missing-import]
    from sqlalchemy import text
    
    # List of migrations to try
    migrations = [
        "ALTER TABLE bookings ADD COLUMN handled_by VARCHAR(100)",
        "ALTER TABLE otp_verifications ADD COLUMN reset_token VARCHAR(255)",
        "ALTER TABLE otp_verifications ADD COLUMN token_expires_at DATETIME",
        "CREATE TABLE IF NOT EXISTS audit_logs (id SERIAL PRIMARY KEY, timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP, user_id INTEGER REFERENCES users(id), user_name VARCHAR(100), action_type VARCHAR(50), description TEXT, ip_address VARCHAR(45))"
    ]
    
    for m in migrations:
        try:
            db.session.execute(text(m))
            db.session.commit()
        except Exception as e:
            print(f"Migration error ({m}): {e}")
            db.session.rollback()


def _seed_data():
    from app.models.service import Service
    from app.models.user import User

    if Service.query.count() == 0:
        db.session.add_all([
            Service(name="General Checkup", icon="🩺", desc="Comprehensive health examination for your pet"),
            Service(name="Vaccination",     icon="💉", desc="Keep your pet protected with up-to-date vaccines"),
            Service(name="Dental Care",     icon="🦷", desc="Professional dental cleaning and oral health care"),
            Service(name="Surgery",         icon="🏥", desc="Advanced surgical procedures with expert veterinarians"),
            Service(name="Grooming",        icon="✂️",  desc="Full grooming services to keep your pet looking great"),
            Service(name="Emergency Care",  icon="🚨", desc="24/7 emergency veterinary care for urgent situations"),
        ])

    _add_user_if_missing('demo@vetsync.com',           'Demo',  'User',         '0000000000', 'client',  'demo123')
    _add_user_if_missing('adminvetclinic@gmail.com',   'Admin', 'VetSync',      '0000000001', 'admin',   'vetadminclinic1214')
    _add_user_if_missing('veterinarian123@gmail.com',  'Staff', 'Veterinarian', '0000000002', 'staff',   'vet121516')

    db.session.commit()


def _add_user_if_missing(email, first, last, contact, role, password):
    from app.models.user import User
    if not User.query.filter_by(email=email).first():
        u = User(first_name=first, last_name=last, email=email, contact=contact, role=role)
        u.set_password(password)
        db.session.add(u)
