import logging

from gunicorn.app.base import BaseApplication

from interstate_love_song._api import API

logger = logging.getLogger(__name__)


class _BaseApp(BaseApplication):
    def __init__(self, application, **options):
        self.application = application
        self.options = options

        super(_BaseApp, self).__init__()

    def load_config(self):
        for key, value in self.options.items():
            if key in self.cfg.settings and value is not None:
                self.cfg.set(key.lower(), value)

            else:
                logger.warning(
                    'Could not find config options "{0}" valid options: {1}'.format(
                        key, ", ".join(self.cfg.settings.keys())
                    )
                )

    def load(self):
        return self.application


if __name__ == "__main__":
    _BaseApp(
        API(),
        **{
            "loglevel": "debug",
            "certfile": "selfsign.crt",
            "keyfile": "selfsign.key",
            "worker_class": "sync",
            #'keepalive':90
        },
    ).run()
    pass
