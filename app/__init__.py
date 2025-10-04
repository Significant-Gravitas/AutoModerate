import logging
import os
import time
from typing import Any, List, Union

import sentry_sdk
from flask import Flask
from flask_login import LoginManager
from flask_socketio import SocketIO
from flask_sqlalchemy import SQLAlchemy
from flask_talisman import Talisman
from flask_wtf.csrf import CSRFProtect

from config.config import config

# SQLAlchemy - database interface
db = SQLAlchemy()
login_manager = LoginManager()
socketio = SocketIO(cors_allowed_origins="*")
csrf = CSRFProtect()


def create_app(config_name: str = 'default') -> Flask:
    app = Flask(__name__)
    app.config.from_object(config[config_name])

    # Initialize Sentry
    if app.config.get('SENTRY_DSN'):
        def before_send(event, hint):
            """Filter out expected errors before sending to Sentry"""
            # Filter out Engine.IO "Invalid session" errors - these are expected when
            # clients lose connection and attempt to use stale session IDs
            if 'exception' in event:
                for exception in event.get('exception', {}).get('values', []):
                    exception_value = exception.get('value', '')
                    if 'Invalid session' in exception_value:
                        # Don't send to Sentry - this is expected connection lifecycle behavior
                        return None

            # Filter out log messages about invalid sessions
            if 'logentry' in event:
                message = event.get('logentry', {}).get('message', '')
                if 'Invalid session' in message:
                    return None

            return event

        sentry_sdk.init(
            dsn=app.config['SENTRY_DSN'],
            send_default_pii=True,
            enable_logs=True,
            traces_sample_rate=1.0,
            environment=app.config.get('FLASK_ENV', 'development'),
            before_send=before_send,
        )

    # Handle HTTPS proxy headers (for production behind reverse proxy)
    from werkzeug.middleware.proxy_fix import ProxyFix
    app.wsgi_app = ProxyFix(app.wsgi_app, x_proto=1, x_host=1)

    # Initialize SQLAlchemy with PostgreSQL
    db.init_app(app)
    use_direct_postgres = app.config.get('USE_DIRECT_POSTGRES', False)

    if use_direct_postgres:
        app.logger.info("Using direct PostgreSQL connection via SQLAlchemy")
        app.logger.info(f"Pool configuration: size={app.config['SQLALCHEMY_ENGINE_OPTIONS']['pool_size']}, "
                        f"max_overflow={app.config['SQLALCHEMY_ENGINE_OPTIONS']['max_overflow']}")
    else:
        app.logger.info("Using SQLAlchemy database")

    # Initialize Flask-Login
    login_manager.init_app(app)
    login_manager.login_view = 'auth.login'
    login_manager.login_message = 'Please log in to access this page.'

    # Initialize SocketIO with increased timeouts to handle browser tab throttling
    # ping_timeout: Time to wait for client response before considering connection dead
    # ping_interval: Time between server pings to check client connection
    socketio.init_app(
        app,
        async_mode='threading',
        ping_timeout=120,  # Increased from default 60s to 2 minutes
        ping_interval=25,  # Keep default 25s interval
        logger=False,      # Disable SocketIO logger to reduce noise
        engineio_logger=False  # Disable Engine.IO logger
    )

    # Disable verbose SocketIO logs
    logging.getLogger('socketio').setLevel(logging.ERROR)
    logging.getLogger('engineio').setLevel(logging.ERROR)

    # Suppress Werkzeug assertion errors from WebSocket disconnections
    # These occur when clients disconnect abruptly and are harmless
    werkzeug_logger = logging.getLogger('werkzeug')
    original_werkzeug_log = werkzeug_logger.error

    def filtered_werkzeug_log(msg, *args, **kwargs):
        """Filter out write() before start_response errors"""
        if isinstance(msg, str) and 'write() before start_response' in msg:
            return  # Suppress this specific error
        return original_werkzeug_log(msg, *args, **kwargs)

    werkzeug_logger.error = filtered_werkzeug_log

    # Initialize CSRF protection
    csrf.init_app(app)

    # Configure CSRF header names for AJAX requests
    app.config['WTF_CSRF_HEADERS'] = ['X-CSRFToken', 'X-CSRF-Token']

    # Initialize security headers with Talisman
    csp = {
        'default-src': "'self'",
        'script-src': [
            "'self'",
            "'unsafe-inline'",  # Required for inline scripts and Bootstrap functionality
            "https://cdn.jsdelivr.net",  # Bootstrap, Chart.js
            "https://cdnjs.cloudflare.com",  # FontAwesome, Socket.IO
            "https://cdn.socket.io",  # Socket.IO CDN
            "https://static.cloudflareinsights.com"  # Cloudflare Analytics
        ],
        'style-src': [
            "'self'",
            "'unsafe-inline'",  # Required for inline styles and Bootstrap
            "https://cdn.jsdelivr.net",  # Bootstrap CSS
            "https://cdnjs.cloudflare.com",  # FontAwesome CSS
            "https://fonts.googleapis.com"  # Google Fonts (if used)
        ],
        'font-src': [
            "'self'",
            "https://fonts.gstatic.com",  # Google Fonts
            "https://cdnjs.cloudflare.com",  # FontAwesome fonts
            "https://cdn.jsdelivr.net",  # Bootstrap fonts
            "data:"  # Data URIs for fonts
        ],
        'img-src': [
            "'self'",
            "data:",  # Required for inline images and icons
            "https:",  # Allow all HTTPS images
            "blob:"  # For dynamic images
        ],
        'connect-src': [
            "'self'",
            "ws:",  # WebSocket connections (dev)
            "wss:",  # Secure WebSocket connections (prod)
            "https://cdn.socket.io",  # Socket.IO connections
            "https://cdn.jsdelivr.net",  # Bootstrap source maps
            "https://cdnjs.cloudflare.com"  # Socket.IO and other CDN source maps
        ]
    }

    Talisman(
        app,
        force_https=True,  # Set to True in production
        strict_transport_security=True,
        strict_transport_security_max_age=31536000,  # 1 year
        content_security_policy=csp,
        referrer_policy='strict-origin-when-cross-origin',
        feature_policy={
            'camera': "'none'",
            'microphone': "'none'",
            'geolocation': "'none'"
        }
    )

    # User loader for Flask-Login
    @login_manager.user_loader
    def load_user(user_id):
        import asyncio
        import concurrent.futures

        from flask import current_app, has_app_context

        from app.services.database_service import db_service

        # Get the current app reference before creating the thread
        if has_app_context():
            app = current_app._get_current_object()
        else:
            # If no app context, return None (user not authenticated)
            return None

        def run_async_with_context():
            def async_operation():
                with app.app_context():
                    return asyncio.run(db_service.get_user_by_id(user_id))

            return async_operation()

        # Run in a separate thread with proper app context
        with concurrent.futures.ThreadPoolExecutor() as executor:
            future = executor.submit(run_async_with_context)
            return future.result()

    # Initialize OAuth
    from app.routes.auth import oauth
    oauth.init_app(app)
    oauth.register(
        name='google',
        client_id=app.config.get('GOOGLE_CLIENT_ID'),
        client_secret=app.config.get('GOOGLE_CLIENT_SECRET'),
        server_metadata_url=app.config.get('GOOGLE_DISCOVERY_URL'),
        client_kwargs={
            'scope': 'openid email profile'
        }
    )

    # Register blueprints
    from app.routes.admin import admin_bp
    from app.routes.api import api_bp
    from app.routes.auth import auth_bp
    from app.routes.dashboard import dashboard_bp
    from app.routes.manual_review import manual_review_bp
    from app.routes.monitoring import monitoring_bp
    from app.routes.websocket import websocket_bp

    app.register_blueprint(auth_bp, url_prefix='/auth')
    app.register_blueprint(dashboard_bp, url_prefix='/dashboard')
    app.register_blueprint(api_bp, url_prefix='/api')
    app.register_blueprint(websocket_bp)
    app.register_blueprint(admin_bp, url_prefix='/admin')
    app.register_blueprint(manual_review_bp)
    app.register_blueprint(monitoring_bp)

    # Exempt API endpoints from CSRF protection (they use API key authentication)
    csrf.exempt(api_bp)

    # Database initialization with retry logic (only in main process, not reloader)
    if not os.environ.get('WERKZEUG_RUN_MAIN'):
        with app.app_context():
            _initialize_database_with_retry(app)

    # Add custom Jinja2 filters
    @app.template_filter('to_dict_list')
    def to_dict_list_filter(items: List[Any]) -> List[Union[dict, Any]]:
        """Convert a list of objects with to_dict() method to a list of dictionaries"""
        if not items:
            return []
        return [item.to_dict() if hasattr(item, 'to_dict') else item for item in items]

    @app.template_filter('format_number')
    def format_number_filter(value):
        """Format numbers with comma separators for readability"""
        if value is None:
            return '0'
        try:
            return '{:,}'.format(int(value))
        except (ValueError, TypeError):
            return str(value)

    return app


def _initialize_database_with_retry(app: Flask, max_retries: int = 3, delay: int = 5) -> None:
    """Initialize database with retry logic for connection pool issues"""
    logger = logging.getLogger(__name__)
    for attempt in range(max_retries):
        try:
            logger.info(f"Attempting database initialization (attempt {attempt + 1}/{max_retries})")
            db.create_all()
            _create_default_admin(app)
            logger.info("Database initialization successful")
            return
        except Exception as e:
            error_msg = str(e).lower()
            if "max clients" in error_msg or "pool" in error_msg:
                logger.warning(f"Database pool issue on attempt {attempt + 1}: {e}")
                if attempt < max_retries - 1:
                    logger.info(f"Waiting {delay} seconds before retry...")
                    time.sleep(delay)
                    delay *= 2  # Exponential backoff
                else:
                    logger.error("Max retries reached. Database initialization failed.")
                    logger.error("Solutions:")
                    logger.error("   1. Check your database connection pool settings")
                    logger.error("   2. Reduce SQLALCHEMY_ENGINE_OPTIONS pool_size in config")
                    logger.error("   3. Contact your database administrator")
                    # Don't exit completely, allow app to start without DB init
                    break
            else:
                logger.error(f"Database error: {e}")
                if attempt < max_retries - 1:
                    logger.info(f"Retrying in {delay} seconds...")
                    time.sleep(delay)
                else:
                    logger.error("Database initialization failed after all retries")
                    break


def _create_default_admin(app: Flask) -> None:
    """Create default admin user"""
    logger = logging.getLogger(__name__)
    try:
        import asyncio

        from app.services.database_service import db_service

        # Use the same pattern as user_loader for async handling
        try:
            loop = asyncio.get_event_loop()
            admin = loop.run_until_complete(
                db_service.get_user_by_email(app.config['ADMIN_EMAIL']))
        except RuntimeError:
            # If no event loop is running, create a new one
            admin = asyncio.run(db_service.get_user_by_email(
                app.config['ADMIN_EMAIL']))

        if not admin:
            try:
                loop = asyncio.get_event_loop()
                admin = loop.run_until_complete(db_service.create_user(
                    username='admin',
                    email=app.config['ADMIN_EMAIL'],
                    password=app.config['ADMIN_PASSWORD'],
                    is_admin=True
                ))
            except RuntimeError:
                admin = asyncio.run(db_service.create_user(
                    username='admin',
                    email=app.config['ADMIN_EMAIL'],
                    password=app.config['ADMIN_PASSWORD'],
                    is_admin=True
                ))
            if admin:
                logger.info(f"Created default admin user: {app.config['ADMIN_EMAIL']}")
            else:
                logger.error("Failed to create default admin user")
    except Exception as e:
        logger.error(f"Error creating default admin user: {e}")
