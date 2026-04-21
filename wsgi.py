"""Production WSGI entry point.

Must be served by gunicorn (or similar) with an eventlet worker class so that
Flask-SocketIO's long-polling transport works. Example:

    gunicorn --worker-class eventlet --workers 1 --bind 0.0.0.0:6217 wsgi:app

Three eventlet-related steps have to happen before ``app`` is imported so the
stdlib, psycopg2, and Flask-SocketIO all agree they're running under eventlet:

1. ``eventlet.monkey_patch()`` — replaces socket/threading/select/ssl with
   cooperative greenlet versions.
2. ``psycogreen.eventlet.patch_psycopg()`` — teaches psycopg2 to yield the
   eventlet loop during blocking DB calls. Without this, each query stalls
   the whole worker and kills concurrency.
3. ``SOCKETIO_ASYNC_MODE=eventlet`` — tells ``app/__init__.py`` to initialise
   SocketIO in eventlet mode. Setting it here (rather than auto-detecting from
   sys.modules) is load-bearing: python-engineio imports eventlet whenever
   it's installed, so auto-detection false-positives the dev server too.
"""
import os

import eventlet

eventlet.monkey_patch()

from psycogreen.eventlet import patch_psycopg  # noqa: E402

patch_psycopg()

os.environ['SOCKETIO_ASYNC_MODE'] = 'eventlet'

from app import create_app  # noqa: E402

app = create_app(os.getenv('FLASK_CONFIG', 'production'))
