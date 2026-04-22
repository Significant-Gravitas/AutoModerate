"""Production WSGI entry point.

Served by gunicorn with the gthread worker class. Example:

    gunicorn --worker-class gthread --workers 1 --threads 50 \
             --bind 0.0.0.0:6217 wsgi:app

Why not eventlet
----------------
We previously used eventlet for WebSocket support but it's incompatible
with Flask's ``async def`` routes under standard decorators
(``flask_login.login_required``, ``flask_limiter.limit``, Flask's own
``@app.route`` on async views). Those decorators call
``flask.current_app.ensure_sync(...)`` which uses ``asgiref.AsyncToSync``
to invoke the async view, which in turn calls ``asyncio.run()``. Under
eventlet's greenlet hub ``asyncio.run()`` raises
"asyncio.run() cannot be called from a running event loop" — so every
authenticated or rate-limited route 500s in production.

gthread + ``SOCKETIO_ASYNC_MODE=threading`` gives us:

- Each request handled by a real OS thread, so asgiref can create a loop.
- Flask-SocketIO in threading mode handles WebSockets via those same
  threads; perfectly fine for our dashboard-scale realtime traffic.
- Identical behaviour in dev (``run.py``) and prod, so there's one less
  axis along which "works on my machine" can happen.
"""
import os

os.environ.setdefault('SOCKETIO_ASYNC_MODE', 'threading')

from app import create_app  # noqa: E402

app = create_app(os.getenv('FLASK_CONFIG', 'production'))
