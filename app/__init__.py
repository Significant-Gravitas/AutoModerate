from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager
from flask_socketio import SocketIO
from config.config import config
import time
import sys
import os

# SQLAlchemy - database interface
db = SQLAlchemy()
login_manager = LoginManager()
socketio = SocketIO(cors_allowed_origins="*")

def create_app(config_name='default'):
    app = Flask(__name__)
    app.config.from_object(config[config_name])
    
    # Initialize SQLAlchemy with PostgreSQL
    db.init_app(app)
    use_direct_postgres = app.config.get('USE_DIRECT_POSTGRES', False)
    
    if use_direct_postgres:
        print("🐘 Using direct PostgreSQL connection via SQLAlchemy")
        print(f"📊 Pool configuration: size={app.config['SQLALCHEMY_ENGINE_OPTIONS']['pool_size']}, "
              f"max_overflow={app.config['SQLALCHEMY_ENGINE_OPTIONS']['max_overflow']}")
    else:
        print("🔄 Using SQLAlchemy database")
    
    # Initialize Flask-Login
    login_manager.init_app(app)
    login_manager.login_view = 'auth.login'
    login_manager.login_message = 'Please log in to access this page.'
    
    # Initialize SocketIO
    socketio.init_app(app, async_mode='threading')
    
    # User loader for Flask-Login
    @login_manager.user_loader
    def load_user(user_id):
        from app.models.user import User
        return User.query.get(user_id)
    
    # Register blueprints
    from app.routes.auth import auth_bp
    from app.routes.dashboard import dashboard_bp
    from app.routes.api import api_bp
    from app.routes.websocket import websocket_bp
    from app.routes.admin import admin_bp
    from app.routes.manual_review import manual_review_bp
    
    app.register_blueprint(auth_bp, url_prefix='/auth')
    app.register_blueprint(dashboard_bp, url_prefix='/dashboard')
    app.register_blueprint(api_bp, url_prefix='/api')
    app.register_blueprint(websocket_bp)
    app.register_blueprint(admin_bp, url_prefix='/admin')
    app.register_blueprint(manual_review_bp)
    
    # Database initialization with retry logic (only in main process, not reloader)
    if not os.environ.get('WERKZEUG_RUN_MAIN'):
        with app.app_context():
            _initialize_database_with_retry(app)
    
    # Add custom Jinja2 filters
    @app.template_filter('to_dict_list')
    def to_dict_list_filter(items):
        """Convert a list of objects with to_dict() method to a list of dictionaries"""
        if not items:
            return []
        return [item.to_dict() if hasattr(item, 'to_dict') else item for item in items]
    
    return app

def _initialize_database_with_retry(app, max_retries=3, delay=5):
    """Initialize database with retry logic for connection pool issues"""
    for attempt in range(max_retries):
        try:
            print(f"🔄 Attempting database initialization (attempt {attempt + 1}/{max_retries})")
            db.create_all()
            _create_default_admin(app)
            print("✅ Database initialization successful")
            return
        except Exception as e:
            error_msg = str(e).lower()
            if "max clients" in error_msg or "pool" in error_msg:
                print(f"⚠️  Database pool issue on attempt {attempt + 1}: {e}")
                if attempt < max_retries - 1:
                    print(f"⏱️  Waiting {delay} seconds before retry...")
                    time.sleep(delay)
                    delay *= 2  # Exponential backoff
                else:
                    print("❌ Max retries reached. Database initialization failed.")
                    print("💡 Solutions:")
                    print("   1. Check your database connection pool settings")
                    print("   2. Reduce SQLALCHEMY_ENGINE_OPTIONS pool_size in config")
                    print("   3. Contact your database administrator")
                    # Don't exit completely, allow app to start without DB init
                    break
            else:
                print(f"❌ Database error: {e}")
                if attempt < max_retries - 1:
                    print(f"⏱️  Retrying in {delay} seconds...")
                    time.sleep(delay)
                else:
                    print("❌ Database initialization failed after all retries")
                    break

def _create_default_admin(app):
    """Create default admin user"""
    try:
        from app.models.user import User
        
        admin = User.query.filter_by(email=app.config['ADMIN_EMAIL']).first()
        if not admin:
            admin = User(
                email=app.config['ADMIN_EMAIL'],
                username='admin',
                is_admin=True
            )
            admin.set_password(app.config['ADMIN_PASSWORD'])
            db.session.add(admin)
            db.session.commit()
            print(f"✅ Created default admin user: {app.config['ADMIN_EMAIL']}")
    except Exception as e:
        print(f"❌ Error creating default admin user: {e}")
