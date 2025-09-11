import os

from dotenv import load_dotenv

load_dotenv()


class Config:
    SECRET_KEY = os.environ.get(
        'SECRET_KEY') or 'dev-secret-key-change-in-production'
    SQLALCHEMY_DATABASE_URI = os.environ.get(
        'DATABASE_URL') or 'sqlite:///automoderate.db'
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    OPENAI_API_KEY = os.environ.get('OPENAI_API_KEY')
    # OpenAI model and token configuration
    OPENAI_CHAT_MODEL = os.environ.get(
        'OPENAI_CHAT_MODEL', 'gpt-5-nano-2025-08-07')
    # Estimated maximum context window size for the selected model
    OPENAI_CONTEXT_WINDOW = int(os.environ.get(
        'OPENAI_CONTEXT_WINDOW', '400000'))
    # Upper bound for output tokens; actual requests may use much less
    OPENAI_MAX_OUTPUT_TOKENS = int(os.environ.get(
        'OPENAI_MAX_OUTPUT_TOKENS', '128000'))
    ADMIN_EMAIL = os.environ.get('ADMIN_EMAIL')
    ADMIN_PASSWORD = os.environ.get('ADMIN_PASSWORD')

    # Database connection preference
    USE_DIRECT_POSTGRES = bool(os.environ.get(
        'DATABASE_URL', '').startswith('postgresql://'))

    # SQLAlchemy connection pool configuration
    SQLALCHEMY_ENGINE_OPTIONS = {
        'pool_size': 5,                    # Number of connections to maintain in pool
        'pool_timeout': 30,                # Seconds to wait for connection from pool
        'pool_recycle': 1800,              # Seconds before recreating connection (30 min)
        'pool_pre_ping': True,             # Verify connections before use
        'max_overflow': 10,                # Additional connections beyond pool_size
        'echo': bool(os.environ.get('SQL_DEBUG', False))  # SQL debugging via env var
    }


class DevelopmentConfig(Config):
    DEBUG = True


class ProductionConfig(Config):
    DEBUG = False


config = {
    'development': DevelopmentConfig,
    'production': ProductionConfig,
    'default': DevelopmentConfig
}
