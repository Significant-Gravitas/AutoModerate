import logging
import os

from flask import Response, redirect, url_for

from app import create_app, socketio

# Configure logging to reduce noise
logging.getLogger('werkzeug').setLevel(
    logging.WARNING)  # Reduce Flask dev server logs
logging.getLogger('socketio').setLevel(logging.WARNING)  # Reduce SocketIO logs
logging.getLogger('engineio').setLevel(logging.WARNING)  # Reduce EngineIO logs

app = create_app(os.getenv('FLASK_CONFIG') or 'default')


@app.route('/')
def home() -> Response:
    return redirect(url_for('auth.login'))


if __name__ == '__main__':
    socketio.run(app, host='0.0.0.0', port=6217)
