import argparse
import logging

from interstate_love_song.mapping import SimpleMapper
from .http import get_falcon_api, BrokerResource, standard_protocol_creator
from .settings import Settings, load_settings_json


def gunicorn_runner(wsgi, host, port, cert, key):
    from gunicorn.app.base import BaseApplication

    class _GunicornApp(BaseApplication):
        def __init__(self, app, options=None):
            self.app = app
            self.options = options or {}
            super().__init__()

        def init(self, parser, opts, args):
            pass

        def load(self):
            return self.app

        def load_config(self):
            config = {
                key: value
                for key, value in self.options.items()
                if key in self.cfg.settings and value is not None
            }
            for key, value in config.items():
                self.cfg.set(key.lower(), value)

    options = {
        "bind": "{}:{}".format(host, port),
        "certfile": cert,
        "keyfile": key,
        "log-level": "debug",
        "worker_class": "gevent",
    }

    _GunicornApp(wsgi, options).run()


def werkzeug_runner(wsgi, host, port, cert, key):
    """Doesn't seem to send chunked responses properly, and so won't work with PCOIP-clients it seems."""
    from werkzeug.serving import run_simple

    run_simple(host, port, wsgi, ssl_context=(cert, key))


def cherrypy_runner(wsgi, host, port, cert, key):
    import cherrypy
    from cherrypy import tree

    tree.graft(wsgi, "/")

    cherrypy.server.ssl_certificate = cert
    cherrypy.server.ssl_private_key = key
    cherrypy.server.bind_addr = (host, port)

    cherrypy.engine.start()
    cherrypy.engine.block()


if __name__ == "__main__":
    argparser = argparse.ArgumentParser("interstate_love_song")
    argparser.add_argument(
        "-s", "--server", choices=["werkzeug", "gunicorn", "cherrypy"], default="gunicorn"
    )
    argparser.add_argument("--host", default="localhost")
    argparser.add_argument("-p", "--port", default=60443, type=int)
    argparser.add_argument(
        "--fallback_sessions", action="store_true", help="Use fallback session management."
    )
    argparser.add_argument("--config", help="Config file.")
    argparser.add_argument("--cert", default="selfsign.crt")
    argparser.add_argument("--key", default="selfsign.key")

    args = argparser.parse_args()

    settings = Settings()
    if args.config:
        with open(args.config, "r") as f:
            settings = load_settings_json(f.read())

    simple_mapper = SimpleMapper(
        settings.simple_mapper.username,
        settings.simple_mapper.password_hash,
        list(settings.simple_mapper.resources),
    )

    wsgi = get_falcon_api(
        BrokerResource(standard_protocol_creator(simple_mapper)),
        settings,
        use_fallback_sessions=args.fallback_sessions,
    )

    if args.server == "werkzeug":
        werkzeug_runner(wsgi, args.host, args.port, args.cert, args.key)
    elif args.server == "gunicorn":
        gunicorn_runner(wsgi, args.host, args.port, args.cert, args.key)
    elif args.server == "cherrypy":
        cherrypy_runner(wsgi, args.host, args.port, args.cert, args.key)
