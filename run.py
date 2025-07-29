from app import create_app, socketio
from flask import redirect, url_for
import os

app = create_app(os.getenv('FLASK_ENV', 'development'))

@app.route('/')
def home():
    return redirect(url_for('auth.login'))

if __name__ == '__main__':
    socketio.run(app, debug=True, host='0.0.0.0', port=6217)
