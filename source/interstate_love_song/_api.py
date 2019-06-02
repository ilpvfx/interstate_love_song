import falcon
import falcon_cors


from falcon_middleware_beaker import BeakerSessionMiddleware

from .resources.broker import BrokerResource


session_opts = {
    "session.type": "file",
    "session.data_dir": "/tmp/",
    "session.auto": True,
}

from beaker.session import SessionObject


class Specialsession(BeakerSessionMiddleware):
    def process_request(self, request, *args):
        if "CLIENT-LOG-ID" in request.headers:

            session = SessionObject(
                request.env, id=request.headers.get("CLIENT-LOG-ID"), **self.options
            )

            request.env[self.environ_key] = session

    def process_response(self, request, response, resource, request_succeded):
        session = request.env.get(self.environ_key, None)

        if not session:
            return

        return super(Specialsession, self).process_request(
            request, response, resource, request_succeded
        )


class API(falcon.API):
    def __init__(self):
        middleware = [
            falcon_cors.CORS(
                allow_all_origins=True, allow_all_headers=True, allow_all_methods=True
            ).middleware
        ]

        super(API, self).__init__(media_type=None, middleware=Specialsession(session_opts))

        print("MIDDLE")

        self.add_route("/pcoip-broker/xml", BrokerResource())

    def start(self):
        raise NotImplementedError("")

    def stop(self):
        raise NotImplementedError("")
