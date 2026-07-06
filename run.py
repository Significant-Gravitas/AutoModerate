"""Development entry point.

For production use ``wsgi:app`` behind gunicorn with the gthread worker class.
This module intentionally refuses to start the Werkzeug dev server when
``FLASK_CONFIG=production`` so a misconfigured deploy fails loudly instead of
quietly serving traffic from an unsafe development server.
"""
import logging
import os

from flask import Response, redirect, url_for

from app import create_app, socketio

# Configure logging to reduce noise
logging.getLogger('werkzeug').setLevel(
    logging.WARNING)  # Reduce Flask dev server logs
logging.getLogger('socketio').setLevel(logging.WARNING)  # Reduce SocketIO logs
logging.getLogger('engineio').setLevel(logging.WARNING)  # Reduce EngineIO logs

_config_name = os.getenv('FLASK_CONFIG') or 'default'
app = create_app(_config_name)


@app.route('/')
def home() -> Response:
    return redirect(url_for('auth.login'))


if __name__ == '__main__':
    if _config_name == 'production':
        raise RuntimeError(
            "run.py starts the Werkzeug development server which is not safe for "
            "production traffic. Serve via gunicorn instead:\n"
            "    gunicorn --worker-class gthread --workers 1 --threads 50 --bind 0.0.0.0:6217 wsgi:app"
        )
    socketio.run(app, host='0.0.0.0', port=6217, allow_unsafe_werkzeug=True)
