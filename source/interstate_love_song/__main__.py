import argparse
import logging
import sys

from interstate_love_song._version import VERSION
from interstate_love_song.mapping import SimpleMapper
from .http import get_falcon_api, BrokerResource, standard_protocol_creator
from .settings import Settings, load_settings_json, MapperToUse

logger = logging.getLogger(__name__)


def gunicorn_runner(wsgi, host, port, cert, key, worker_class="gevent", workers=2):
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
        "worker_class": worker_class,
        "workers": workers,
    }

    logger.info("Running gunicorn.")
    _GunicornApp(wsgi, options).run()


def werkzeug_runner(wsgi, host, port, cert, key):
    """Doesn't seem to send chunked responses properly, and so won't work with PCOIP-clients it seems."""
    from werkzeug.serving import run_simple

    logger.info("Running werkzeug.")
    run_simple(host, port, wsgi, ssl_context=(cert, key))


def cherrypy_runner(wsgi, host, port, cert, key):
    import cherrypy
    from cherrypy import tree

    tree.graft(wsgi, "/")

    cherrypy.server.ssl_certificate = cert
    cherrypy.server.ssl_private_key = key
    cherrypy.server.bind_addr = (host, port)

    logger.info("Running cherrypy.")

    cherrypy.engine.start()
    cherrypy.engine.block()


def print_logo():
    data = """
             ________      _____                   _____       _____      
         ____  _/________  /_____________________  /______ __  /_____ 
          __  / __  __ \  __/  _ \_  ___/_  ___/  __/  __ `/  __/  _ \\
         __/ /  _  / / / /_ /  __/  /   _(__  )/ /_ / /_/ // /_ /  __/
         /___/  /_/ /_/\__/ \___//_/    /____/ \__/ \__,_/ \__/ \___/ 
                                                                      
          ______                         ________                     
          ___  / _________   ______      __  ___/___________________ _
          __  /  _  __ \_ | / /  _ \     _____ \_  __ \_  __ \_  __ `/
          _  /___/ /_/ /_ |/ //  __/     ____/ // /_/ /  / / /  /_/ / 
          /_____/\____/_____/ \___/      /____/ \____//_/ /_/_\__, /  v{}
                                                             /____/
          
    """.format(
        VERSION
    )
    print(data)
    sys.stdout.flush()


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
    argparser.add_argument(
        "--gunicorn-worker-class", default="gevent", help="only matters if -s gunicorn."
    )
    argparser.add_argument(
        "--gunicorn-workers", default=2, type=int, help="only matters if -s gunicorn."
    )
    argparser.add_argument("--no-splash", action="store_true")

    args = argparser.parse_args()

    if not args.no_splash:
        print_logo()
    else:
        logger.info("Version %s", VERSION)

    logging.basicConfig(level=logging.INFO)

    settings = Settings()
    if args.config:
        with open(args.config, "r") as f:
            settings = load_settings_json(f.read())

    mapper = None
    if settings.mapper == MapperToUse.SIMPLE:
        mapper = SimpleMapper(
            settings.simple_mapper.username,
            settings.simple_mapper.password_hash,
            list(settings.simple_mapper.resources),
        )
    else:
        logger.critical("Unknown mapper %s", settings.mapper)

    logger.info("Server %s, bound to %s:%s", args.server, args.host, args.port)
    logger.info("Mapper: %s;", mapper.name)
    logger.info("SSL; cert: %s; pkey: %s;", args.cert, args.key)

    wsgi = get_falcon_api(
        BrokerResource(standard_protocol_creator(mapper)),
        settings,
        use_fallback_sessions=args.fallback_sessions,
    )

    if args.server == "werkzeug":
        werkzeug_runner(wsgi, args.host, args.port, args.cert, args.key)
    elif args.server == "gunicorn":
        gunicorn_runner(
            wsgi,
            args.host,
            args.port,
            args.cert,
            args.key,
            worker_class=args.gunicorn_worker_class,
            workers=args.gunicorn_workers,
        )
    elif args.server == "cherrypy":
        cherrypy_runner(wsgi, args.host, args.port, args.cert, args.key)
    else:
        logger.critical("Unknown server type %s", args.server)
