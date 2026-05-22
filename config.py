import os
from datetime import timedelta

class Config:
    SECRET_KEY = os.getenv('SECRET_KEY', 'vetsync-secret-key-2024')
    _database_url = os.getenv(
        'DATABASE_URL',
        'postgresql://username:password@localhost:5432/vetsync_db'
    )
    if _database_url.startswith('postgres://'):
        _database_url = _database_url.replace('postgres://', 'postgresql://', 1)
    SQLALCHEMY_DATABASE_URI = _database_url
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    SQLALCHEMY_ENGINE_OPTIONS = {
        "pool_pre_ping": True,
        "pool_recycle": 300,
    }
    AUTO_CREATE_DB = os.getenv('AUTO_CREATE_DB', 'false').lower() == 'true'
    JWT_SECRET_KEY = os.getenv('JWT_SECRET_KEY', 'supergit-secret-jwt-key')
    JWT_ACCESS_TOKEN_EXPIRES = timedelta(minutes=15)

    MAIL_SERVER = 'smtp.gmail.com'
    MAIL_PORT = 587
    MAIL_USE_TLS = True
    MAIL_USERNAME = os.getenv('MAIL_USERNAME')
    MAIL_PASSWORD = os.getenv('MAIL_PASSWORD')

    # VETSYNC SECURITY MATRIX: Secure In-Transit Session Cookies & Session Security
    # Enforces industry-standard session protections globally:
    # 1. HttpOnly = True ensures session identifiers cannot be read by client-side JavaScript,
    #    neutralizing cookie-stealing Trojan malware.
    # 2. SameSite = 'Lax' limits cookie transmission to top-level cross-site requests, mitigating
    #    Cross-Site Request Forgery (CSRF) attempts.
    # 3. Permanent Session Lifetime = 2 hours bounds session state lifespan.
    # 4. ENFORCE_HTTPS enforces secure SSL/TLS communication layers.
    SESSION_COOKIE_HTTPONLY = True
    SESSION_COOKIE_SAMESITE = 'Lax'
    PERMANENT_SESSION_LIFETIME = timedelta(hours=2)
    ENFORCE_HTTPS = os.getenv('ENFORCE_HTTPS', 'false').lower() == 'true'


    VAPID_PUBLIC_KEY = os.getenv(
        'VAPID_PUBLIC_KEY',
        'BD9p1qDG9s8ff3E9K8QSjd1KCtzNf1wOj3mFJC60VwhTgQ0WmBoKI9BrLCMpQgo_fyFBVVWrJu6FVgqx4JbhtjA'
    )
    VAPID_PRIVATE_KEY = os.getenv('VAPID_PRIVATE_KEY', (
        '-----BEGIN PRIVATE KEY-----\n'
        'MIGHAgEAMBMGByqGSM49AgEGCCqGSM49AwEHBG0wawIBAQQgtlD6aKe4UjqV0pRZ\n'
        'G/e0jvc0nrodnWeNoZcVAsjEb0mhRANCAAQ/adagxvbPH39xPSvEEo3dSgrczX9c\n'
        'Do95hSQutFcIU4ENFpgaCiPQaywjKUIKP38hQVVVqybuhVYKseCW4bYw\n'
        '-----END PRIVATE KEY-----'
    ))
    VAPID_CLAIMS = {'sub': os.getenv('VAPID_CLAIM_EMAIL', 'mailto:admin@vetsync.com')}


class DevelopmentConfig(Config):
    DEBUG = True
    SESSION_COOKIE_SECURE = False
    AUTO_CREATE_DB = os.getenv('AUTO_CREATE_DB', 'false').lower() == 'true'


class ProductionConfig(Config):
    # VETSYNC SECURITY MATRIX: Production Hardening
    # Enforces production-grade defenses:
    # 1. DEBUG = False prevents full system stack trace disclosure to users in error screens.
    # 2. Session Cookie Secure = True forces browser cookies to be transmitted exclusively over
    #    encrypted HTTPS connections, neutralizing network sniffing/eavesdropping.
    # 3. Enforce HTTPS = True enforces global SSL redirection.
    DEBUG = False
    SESSION_COOKIE_SECURE = True
    ENFORCE_HTTPS = os.getenv('ENFORCE_HTTPS', 'true').lower() == 'true'



config = {
    'development': DevelopmentConfig,
    'production': ProductionConfig,
    'default': DevelopmentConfig,
}
