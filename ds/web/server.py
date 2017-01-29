import os
import base64
import logging

from aiohttp import web
from aiohttp_session import session_middleware
from aiohttp_session.cookie_storage import EncryptedCookieStorage
from cryptography.fernet import Fernet
import aiohttp_jinja2
import jinja2

from . import urls


def root_package_name():
    return __name__.split('.')[0]


def root_package_path(relative_path=None):
    root_module = __import__(root_package_name())
    path = os.path.dirname(os.path.abspath(root_module.__file__))
    if relative_path is not None:
        path = os.path.join(path, relative_path)
    return path


class WebServer:
    def __init__(self, config, db, loop=None):
        self._cfg = config
        self._loop = loop
        self._srv = None
        self._handler = None
        self.log = logging.getLogger(__name__)

        # Fernet key must be 32 bytes.
        cookie_secret = config.get('http', 'cookie_secret', fallback=None)
        cookie_secret = base64.urlsafe_b64decode(cookie_secret or Fernet.generate_key())

        middlewares = [
            session_middleware(EncryptedCookieStorage(cookie_secret)),
        ]
        app = web.Application(middlewares=middlewares)
        app.ioloop = loop
        app.db = db

        aiohttp_jinja2.setup(app,
            loader=jinja2.FileSystemLoader(root_package_path('web/templates')))

        def make_prefixed_router(url_prefix=''):
            def add_route(method, url, *args, **kwargs):
                return app.router.add_route(method, url_prefix + url, *args, **kwargs)
            return add_route

        urls.configure(make_prefixed_router())

        app.router.add_static('/', root_package_path('web/static'), name='static')

        self._app = app

    async def start(self):
        host, port = self._cfg.get('http', 'bind', fallback='127.0.0.1:8000').split(':')
        self.log.info('listen on http://%s:%s/', host, port)
        self._handler = self._app.make_handler()
        self._srv = await self._loop.create_server(self._handler, host, port)

    async def stop(self):
        await self._handler.finish_connections(1.0)
        self._app.db.close()
        self._srv.close()
        await self._srv.wait_closed()
        await self._app.finish()
