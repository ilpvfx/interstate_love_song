import falcon
import falcon_cors


from .resources.broker import BrokerResource


class API(falcon.API):
    def __init__(self):
        middleware = [
            falcon_cors.CORS(
                allow_all_origins=True, allow_all_headers=True, allow_all_methods=True
            ).middleware
        ]

        super(API, self).__init__(middleware=middleware)

        self.add_route("/pcoip-broker/xml", BrokerResource())

    def start(self):
        raise NotImplementedError("")

    def stop(self):
        raise NotImplementedError("")
