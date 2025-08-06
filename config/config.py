import os
from dotenv import load_dotenv

load_dotenv()

class Config:
    SECRET_KEY = os.environ.get('SECRET_KEY') or 'dev-secret-key-change-in-production'
    SQLALCHEMY_DATABASE_URI = os.environ.get('DATABASE_URL') or 'sqlite:///automoderate.db'
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    OPENAI_API_KEY = os.environ.get('OPENAI_API_KEY')
    ADMIN_EMAIL = os.environ.get('ADMIN_EMAIL') or 'admin@example.com'
    ADMIN_PASSWORD = os.environ.get('ADMIN_PASSWORD') or 'admin123'
    
    # Database connection preference
    USE_DIRECT_POSTGRES = bool(os.environ.get('DATABASE_URL', '').startswith('postgresql://'))
    
    # SQLAlchemy connection pool configuration
    SQLALCHEMY_ENGINE_OPTIONS = {
        'pool_size': 5,                    # Number of connections to maintain in pool
        'pool_timeout': 30,                # Seconds to wait for connection from pool
        'pool_recycle': 1800,              # Seconds before recreating connection (30 min)
        'pool_pre_ping': True,             # Verify connections before use
        'max_overflow': 10,                # Additional connections beyond pool_size
        'echo': False                      # Set to True for SQL debugging
    }

class DevelopmentConfig(Config):
    DEBUG = True
    # Smaller pool for development
    SQLALCHEMY_ENGINE_OPTIONS = {
        'pool_size': 3,
        'pool_timeout': 20,
        'pool_recycle': 1800,
        'pool_pre_ping': True,
        'max_overflow': 5,
        'echo': bool(os.environ.get('SQL_DEBUG', False))
    }

class ProductionConfig(Config):
    DEBUG = False
    # Larger pool for production
    SQLALCHEMY_ENGINE_OPTIONS = {
        'pool_size': 10,
        'pool_timeout': 30,
        'pool_recycle': 1800,
        'pool_pre_ping': True,
        'max_overflow': 20,
        'echo': False
    }

config = {
    'development': DevelopmentConfig,
    'production': ProductionConfig,
    'default': DevelopmentConfig
}
