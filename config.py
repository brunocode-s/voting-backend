import os
from datetime import timedelta
from dotenv import load_dotenv

load_dotenv()


class Config:
    """Base configuration"""

    # ── Flask ─────────────────────────────────────────────────────────────────
    SECRET_KEY = os.getenv('SECRET_KEY')
    DEBUG      = os.getenv('FLASK_DEBUG', 'False').lower() == 'true'
    HOST       = os.getenv('FLASK_HOST', '0.0.0.0')
    PORT       = int(os.getenv('FLASK_PORT', '5001'))

    # ── Database ──────────────────────────────────────────────────────────────
    SQLALCHEMY_DATABASE_URI        = os.getenv('DATABASE_URL')
    SQLALCHEMY_TRACK_MODIFICATIONS = False

    # ── Session ───────────────────────────────────────────────────────────────
    SESSION_TYPE               = os.getenv('SESSION_TYPE', 'filesystem')
    SESSION_PERMANENT          = os.getenv('SESSION_PERMANENT', 'False').lower() == 'true'
    PERMANENT_SESSION_LIFETIME = timedelta(
        hours=int(os.getenv('SESSION_LIFETIME_HOURS', '2'))
    )

    # ── CORS ──────────────────────────────────────────────────────────────────
    CORS_ORIGINS = os.getenv('CORS_ORIGINS', '*').split(',')

    # ── App identity ──────────────────────────────────────────────────────────
    APP_NAME  = 'Intelligent Voting System'

    # ── WebAuthn / Biometric ──────────────────────────────────────────────────
    RP_ID     = os.environ.get('RP_ID',     'localhost')
    RP_ORIGIN = os.environ.get('RP_ORIGIN', 'http://localhost:5173')
    # WebAuthn challenge timeout (milliseconds)
    WEBAUTHN_TIMEOUT = 60000
    # How long a biometric verification stays valid for voting (seconds)
    BIOMETRIC_VERIFICATION_VALIDITY = 300

    # ── Email ─────────────────────────────────────────────────────────────────
    MAIL_SERVER         = os.getenv('MAIL_SERVER')
    MAIL_PORT           = int(os.getenv('MAIL_PORT', 587))
    MAIL_USE_TLS        = os.getenv('MAIL_USE_TLS', 'True').lower() == 'true'
    MAIL_USERNAME       = os.getenv('MAIL_USERNAME')
    MAIL_PASSWORD       = os.getenv('MAIL_PASSWORD')
    MAIL_DEFAULT_SENDER = os.getenv('MAIL_DEFAULT_SENDER', 'noreply@votingsystem.com')

    # ── Frontend ──────────────────────────────────────────────────────────────
    FRONTEND_URL = os.getenv('FRONTEND_URL', 'http://localhost:5173')

    # ── Security ──────────────────────────────────────────────────────────────
    BCRYPT_LOG_ROUNDS  = int(os.getenv('BCRYPT_LOG_ROUNDS', 12))
    MAX_LOGIN_ATTEMPTS = int(os.getenv('MAX_LOGIN_ATTEMPTS', 5))

    # ── NIN Verification (Korapay) ────────────────────────────────────────────
    # false → mock mode: any 11-digit NIN accepted, NIns starting '000' fail
    # true  → live Korapay API calls (requires KORAPAY_API_KEY)
    NIN_VERIFICATION_ENABLED = os.getenv('NIN_VERIFICATION_ENABLED', 'false').lower() == 'true'
    KORAPAY_API_KEY           = os.getenv('KORAPAY_API_KEY')
    # Set once before first production deploy — NEVER change afterwards.
    # Changing this invalidates every stored NIN hash in the database.
    NIN_HASH_SALT             = os.getenv('NIN_HASH_SALT', 'change_before_deploy')

    # ── ML / Fraud detection ──────────────────────────────────────────────────
    ML_MODEL_PATH      = os.getenv('ML_MODEL_PATH', './models')
    ANOMALY_THRESHOLD  = float(os.getenv('ANOMALY_THRESHOLD', 0.45))
    CONTAMINATION_RATE = float(os.getenv('CONTAMINATION_RATE', 0.1))

    # ── Blockchain ────────────────────────────────────────────────────────────
    BLOCKCHAIN_ENABLED     = os.getenv('BLOCKCHAIN_ENABLED', 'False').lower() == 'true'
    BLOCKCHAIN_RPC_URL     = os.getenv('BLOCKCHAIN_RPC_URL')
    BLOCKCHAIN_PRIVATE_KEY = os.getenv('BLOCKCHAIN_PRIVATE_KEY')
    VOTE_ENCRYPTION_KEY    = os.getenv('VOTE_ENCRYPTION_KEY')
    VOTER_ID_SALT          = os.getenv('VOTER_ID_SALT', 'default_salt')

    # ── Voting window ─────────────────────────────────────────────────────────
    VOTING_START_DATE = os.getenv('VOTING_START_DATE')
    VOTING_END_DATE   = os.getenv('VOTING_END_DATE')


class DevelopmentConfig(Config):
    """Development configuration"""
    DEBUG = True


class ProductionConfig(Config):
    """Production configuration"""
    DEBUG = False

    # Harden cookies in production
    SESSION_COOKIE_SECURE   = True
    SESSION_COOKIE_HTTPONLY = True
    SESSION_COOKIE_SAMESITE = 'Lax'


class TestingConfig(Config):
    """Testing configuration"""
    TESTING                  = True
    SQLALCHEMY_DATABASE_URI  = 'sqlite:///:memory:'
    NIN_VERIFICATION_ENABLED = False   # always mock in tests
    BCRYPT_LOG_ROUNDS        = 4       # faster hashing in tests


config = {
    'development': DevelopmentConfig,
    'production':  ProductionConfig,
    'testing':     TestingConfig,
    'default':     DevelopmentConfig,
}