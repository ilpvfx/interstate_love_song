import argparse
import logging

from .http import get_falcon_api, BrokerResource


def gunicorn_runner(wsgi, host, port):
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
        "certfile": "selfsign.crt",
        "keyfile": "selfsign.key",
        "log-level": "debug",
    }
    _GunicornApp(wsgi, options).run()


def werkzeug_runner(wsgi, host, port):
    """Doesn't seem to send chunked responses properly, and so won't work with PCOIP-clients it seems."""
    from werkzeug.serving import run_simple

    run_simple(host, port, wsgi, ssl_context=("selfsign.crt", "selfsign.key"))


def cherrypy_runner(wsgi, host, port):
    import cherrypy
    from cherrypy import tree

    tree.graft(wsgi, "/")

    cherrypy.server.ssl_certificate = "selfsign.crt"
    cherrypy.server.ssl_private_key = "selfsign.key"
    cherrypy.server.bind_addr = (host, port)

    cherrypy.engine.start()
    cherrypy.engine.block()


if __name__ == "__main__":
    logging.basicConfig(level="INFO")

    argparser = argparse.ArgumentParser("interstate_love_song")
    argparser.add_argument(
        "-s", "--server", choices=["werkzeug", "gunicorn", "cherrypy"], default="gunicorn"
    )
    argparser.add_argument("--host", default="localhost")
    argparser.add_argument("-p", "--port", default=60443, type=int)

    args = argparser.parse_args()

    wsgi = get_falcon_api(BrokerResource())

    twisted_runner(wsgi, args.host, args.port)

    if args.server == "werkzeug":
        werkzeug_runner(wsgi, args.host, args.port)
    elif args.server == "gunicorn":
        gunicorn_runner(wsgi, args.host, args.port)
    elif args.server == "cherrypy":
        cherrypy_runner(wsgi, args.host, args.port)
