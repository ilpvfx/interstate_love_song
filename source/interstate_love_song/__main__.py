from gunicorn.app.base import BaseApplication
from .http import get_falcon_api, BrokerResource


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


if __name__ == "__main__":
    options = {
        "bind": "localhost:60444",
        "certfile": "selfsign.crt",
        "keyfile": "selfsign.key",
    }
    _GunicornApp(get_falcon_api(BrokerResource()), options).run()
