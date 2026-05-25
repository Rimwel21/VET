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

    # Context processor — injects current_user, csrf_token, and jwt_token into every template
    @app.context_processor
    def inject_globals():
        from app.models.user import User
        from app.utils.security import generate_csrf_token
        from app.services.auth_service import create_jwt_token
        uid = session.get('user_id')
        current_user = db.session.get(User, uid) if uid else None
        
        jwt_token = ""
        if current_user:
            try:
                jwt_token = create_jwt_token(current_user.id, current_user.role)
            except Exception as jwt_err:
                print(f"[JWT Context Processor Error]: {jwt_err}")
                
        return dict(current_user=current_user, csrf_token=generate_csrf_token, jwt_token=jwt_token)

    # Run dynamic schema migrations on application startup
    with app.app_context():
        _run_migrations()
        if app.config.get('AUTO_CREATE_DB'):
            db.create_all()
            _seed_data()
        _enforce_single_admin()
            
    # SECURITY IMPLEMENTATION: Error Handling & Data Leak Prevention
    # Masks HTTP 500 internal server errors to prevent the application from leaking
    # internal database schemas, file paths, or system tracebacks to end users.
    # NOTE: Only handles explicit HTTP 500 responses - NOT all Python exceptions.
    # Catching all Exception types here would intercept route-level try-except blocks
    # and prevent JSON API routes (like /staff/send-custom-push) from returning
    # proper error responses to the frontend JavaScript.
    @app.errorhandler(500)
    def handle_internal_server_error(error):
        from flask import request, jsonify, render_template
        if request.is_json or request.path.startswith('/api/') or request.path.startswith('/staff/'):
            return jsonify({'error': 'An internal server error occurred. Please try again.'}), 500
        return render_template('offline.html'), 500

    @app.errorhandler(413)
    def handle_payload_too_large(error):
        from flask import request, jsonify, flash, redirect
        message = 'Request payload is too large.'
        if (
            request.is_json
            or request.headers.get('X-Requested-With') == 'XMLHttpRequest'
            or request.path.startswith('/api/')
            or request.path.startswith('/staff/')
        ):
            return jsonify({'error': message}), 413
        flash(message, 'error')
        return redirect(request.referrer or '/')

    from app.utils.validation import ValidationError

    @app.errorhandler(ValidationError)
    def handle_validation_error(error):
        from flask import request, jsonify, flash, redirect

        message = error.message
        if (
            request.is_json
            or request.headers.get('X-Requested-With') == 'XMLHttpRequest'
            or request.path.startswith('/api/')
            or request.path.startswith('/staff/')
        ):
            return jsonify({'error': message, 'field': error.field}), error.code
        flash(message, 'error')
        return redirect(request.referrer or '/')
        
    return app
def _run_migrations():
    """Applies simple schema migrations that may be missing in older DBs."""
    # pyrefly: ignore [missing-import]
    from sqlalchemy import inspect, text

    inspector = inspect(db.engine)
    existing_tables = set(inspector.get_table_names())
    if not existing_tables:
        return

    # SECURITY: Schema hardening only runs against tables and columns that already exist.
    # Column-by-column checks avoid dialect-specific ALTER TABLE syntax issues while keeping
    # legacy deployments synchronized with the current security fields.
    migrations = []

    def has_column(table_name, column_name):
        return column_name in {col['name'] for col in inspector.get_columns(table_name)}

    if 'bookings' in existing_tables and not has_column('bookings', 'handled_by'):
        migrations.append("ALTER TABLE bookings ADD COLUMN handled_by VARCHAR(100)")
    if 'otp_verifications' in existing_tables:
        if not has_column('otp_verifications', 'reset_token'):
            migrations.append("ALTER TABLE otp_verifications ADD COLUMN reset_token VARCHAR(255)")
        if not has_column('otp_verifications', 'token_expires_at'):
            migrations.append("ALTER TABLE otp_verifications ADD COLUMN token_expires_at TIMESTAMP")
    if 'users' in existing_tables:
        if not has_column('users', 'push_enabled'):
            migrations.append("ALTER TABLE users ADD COLUMN push_enabled BOOLEAN DEFAULT TRUE")
        if not has_column('users', 'privacy_consent'):
            migrations.append("ALTER TABLE users ADD COLUMN privacy_consent BOOLEAN DEFAULT FALSE")
        if not has_column('users', 'privacy_consent_at'):
            migrations.append("ALTER TABLE users ADD COLUMN privacy_consent_at TIMESTAMP")
    if 'audit_logs' not in existing_tables and 'users' in existing_tables:
        migrations.append(
            "CREATE TABLE IF NOT EXISTS audit_logs (id SERIAL PRIMARY KEY, timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP, user_id INTEGER REFERENCES users(id), user_name VARCHAR(100), action_type VARCHAR(50), description TEXT, ip_address VARCHAR(45))"
        )
    
    for m in migrations:
        try:
            db.session.execute(text(m))
            db.session.commit()
        except Exception as e:
            # Only print if it's not a duplicate column error to avoid noise
            if "already exists" not in str(e).lower():
                print(f"Migration error ({m}): {e}")
            db.session.rollback()


def _seed_data():
    from app.models.service import Service
    from app.models.user import User

    if Service.query.count() == 0:
        db.session.add_all([
            Service(name="General Checkup", icon="🩺", desc="Comprehensive health examination for your pet"), # type: ignore
            Service(name="Vaccination",     icon="💉", desc="Keep your pet protected with up-to-date vaccines"), # type: ignore
            Service(name="Dental Care",     icon="🦷", desc="Professional dental cleaning and oral health care"), # type: ignore
            Service(name="Surgery",         icon="🏥", desc="Advanced surgical procedures with expert veterinarians"), # type: ignore
            Service(name="Grooming",        icon="✂️",  desc="Full grooming services to keep your pet looking great"), # type: ignore
            Service(name="Emergency Care",  icon="🚨", desc="24/7 emergency veterinary care for urgent situations"), # type: ignore
        ])

    _add_user_if_missing('demo@vetsync.com',           'Demo',  'User',         '0000000000', 'client',  'demo123')
    _add_user_if_missing('adminvetclinic@gmail.com',   'Admin', 'VetSync',      '0000000001', 'admin',   'vetadminclinic1214')
    _add_user_if_missing('veterinarian123@gmail.com',  'Staff', 'Staff',        '0000000002', 'staff',   'vet121516')

    db.session.commit()


def _add_user_if_missing(email, first, last, contact, role, password):
    from app.models.user import User
    if not User.query.filter_by(email=email).first():
        u = User(first_name=first, last_name=last, email=email, contact=contact, role=role) # type: ignore
        u.set_password(password)
        db.session.add(u)


def _enforce_single_admin():
    """Ensure only one admin account exists (adminvetclinic@gmail.com).
    Removes any other admin-role accounts and guarantees the canonical
    admin credentials are always correct.
    """
    # SECURITY: Startup RBAC integrity check.
    # This runs only after the schema exists, so fresh QA/test databases can boot cleanly
    # before tables are created. It prevents unauthorized persistent admin accounts.
    from sqlalchemy import inspect
    from app.models.user import User
    ADMIN_EMAIL    = 'adminvetclinic@gmail.com'
    ADMIN_PASSWORD = 'vetadminclinic1214'

    if 'users' not in inspect(db.engine).get_table_names():
        return

    # Ensure the canonical admin exists
    admin = User.query.filter_by(email=ADMIN_EMAIL).first()
    if not admin:
        admin = User(
            first_name='Admin',
            last_name='VetSync',
            email=ADMIN_EMAIL,
            contact='0000000001',
            role='admin',
            is_active=True
        )
        admin.set_password(ADMIN_PASSWORD)
        db.session.add(admin)
        db.session.commit()
        print(f'[BOOT] Canonical admin account created: {ADMIN_EMAIL}')
    else:
        # Always ensure admin account is active, has the right role, and correct password
        changed = False
        if admin.role != 'admin':
            admin.role = 'admin'
            changed = True
        if not admin.is_active:
            admin.is_active = True
            changed = True
        if not admin.check_password(ADMIN_PASSWORD):
            admin.set_password(ADMIN_PASSWORD)
            changed = True
        if changed:
            db.session.commit()
            print(f'[BOOT] Canonical admin account credentials updated/corrected.')

    # Demote any other admin-role accounts to client to enforce single-admin constraint
    # while preserving database referential integrity (e.g. audit logs, bookings)
    extra_admins = (User.query
                    .filter_by(role='admin')
                    .filter(User.email != ADMIN_EMAIL)
                    .all())
    if extra_admins:
        for u in extra_admins:
            print(f'[BOOT] Demoting unauthorized admin account: {u.email}')
            u.role = 'client'
        db.session.commit()
