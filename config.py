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
    JWT_SECRET_KEY = os.getenv('JWT_SECRET_KEY', 'super-secret-jwt-key')
    JWT_ACCESS_TOKEN_EXPIRES = timedelta(minutes=15)

    MAIL_SERVER = 'smtp.gmail.com'
    MAIL_PORT = 587
    MAIL_USE_TLS = True
    MAIL_USERNAME = os.getenv('MAIL_USERNAME')
    MAIL_PASSWORD = os.getenv('MAIL_PASSWORD')

    SESSION_COOKIE_HTTPONLY = True
    SESSION_COOKIE_SAMESITE = 'Lax'
    PERMANENT_SESSION_LIFETIME = timedelta(hours=2)
    ENFORCE_HTTPS = os.getenv('ENFORCE_HTTPS', 'false').lower() == 'true'

    VAPID_PUBLIC_KEY = os.getenv('VAPID_PUBLIC_KEY')
    VAPID_PRIVATE_KEY = os.getenv('VAPID_PRIVATE_KEY')
    VAPID_CLAIMS = {'sub': os.getenv('VAPID_CLAIM_EMAIL', 'mailto:admin@vetsync.com')}


class DevelopmentConfig(Config):
    DEBUG = True
    SESSION_COOKIE_SECURE = False
    AUTO_CREATE_DB = os.getenv('AUTO_CREATE_DB', 'false').lower() == 'true'


class ProductionConfig(Config):
    DEBUG = False
    SESSION_COOKIE_SECURE = True
    ENFORCE_HTTPS = os.getenv('ENFORCE_HTTPS', 'true').lower() == 'true'


config = {
    'development': DevelopmentConfig,
    'production': ProductionConfig,
    'default': DevelopmentConfig,
}
