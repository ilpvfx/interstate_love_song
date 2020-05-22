import logging
from abc import ABC, abstractmethod
from io import BytesIO

from falcon.util import compat
from typing import Callable, Any, Optional
from xml.etree.ElementTree import ParseError, ElementTree

import falcon
from defusedxml.ElementTree import fromstring
from falcon import API
from falcon_middleware_beaker import BeakerSessionMiddleware
from beaker.session import SessionObject


from ._version import VERSION
from .mapping import Mapper
from .protocol import ProtocolHandler, ProtocolSession, BrokerProtocolHandler
from .serialization import serialize_message, deserialize_message
from .settings import Settings

ProtocolCreator = Callable[[], ProtocolHandler]

logger = logging.getLogger(__name__)


def standard_protocol_creator(mapper: Mapper):
    """Curries a creator function with the given mapper. The creator returns a BrokerProtocolHandler."""

    def creator():
        return BrokerProtocolHandler(mapper, mapper.allocate_session)

    return creator


class SessionSetter(ABC):
    """Sets the session data.

    .. note::
        This seemingly unnecessary type is here solely for testing. We want to make sure the endpoint sets session data
        when it should and we can't inspect the request. So we need to dependency inject an intermediary.
    """

    @abstractmethod
    def set_data(self, data: Optional[ProtocolSession]):
        pass

    @abstractmethod
    def get_data(self):
        pass


class BeakerSessionSetter(SessionSetter):
    """The default session setter. Unless you are testing, you want to use this."""

    def __init__(self, request):
        self._request = request

    def set_data(self, data: Optional[ProtocolSession]):
        self._request.env["beaker.session"]["protocol"] = data

    def get_data(self):
        if "protocol" not in self._request.env["beaker.session"]:
            return None
        return self._request.env["beaker.session"]["protocol"]


SessionSetterCreator = Callable[[Any], SessionSetter]


def beaker_session_creator(request) -> SessionSetter:
    """Creates BeakerSessionSetters from requests.. This should be your default unless you are testing."""
    return BeakerSessionSetter(request)


class BrokerResource:
    """The HTTP endpoint for the Broker, where all the communication with a client begins."""

    def __init__(
        self,
        protocol_creator: ProtocolCreator,
        serialize=serialize_message,
        deserialize=deserialize_message,
        session_setter_creator: SessionSetterCreator = beaker_session_creator,
    ):
        """
        :param protocol_creator:
            Creates protocol handlers.
        :param serialize:
            The serialize function for messages.
        :param deserialize:
            The deserialize function for messages.
        :param session_setter_creator:
            Creates session setters. You don't need to touch this except when testing.
        :raise ValueError:
            A parameter was not callable.
        """
        if not all(
            map(callable, [protocol_creator, serialize, deserialize, session_setter_creator])
        ):
            raise ValueError("A parameter was not callable.")
        self._protocol_creator = protocol_creator
        self._serialize = serialize
        self._deserialize = deserialize
        self._session_setter_creator = session_setter_creator

    def on_post(self, req, resp):
        """Receives an XML payload, decodes it and runs it through the protocol. This endpoint is stateful."""
        protocol = self._protocol_creator()

        session_setter = self._session_setter_creator(req)

        try:
            xml_str = req.bounded_stream.read()
            xml = fromstring(xml_str)

            in_msg = self._deserialize(xml)

            logger.debug("Received POST: Message: %s.", str(in_msg))

            new_session_data, out_msg = protocol(in_msg, session_setter.get_data())
            session_setter.set_data(new_session_data)

            if out_msg is None:
                logger.warning(
                    "protocol returned None as the response, this MIGHT mean sessions are not working as they should."
                )
                raise falcon.HTTPInternalServerError(
                    description="Unexpected message received, probably a bug."
                )

            f = BytesIO()
            ElementTree(self._serialize(out_msg)).write(f, encoding="utf-8", xml_declaration=True)

            # WE MUST RETURN A CHUNKED STREAM, OR TERADICI WILL BE VERY UNHAPPY.
            # DON'T JUST CHANGE THIS TO resp.body = blabla, AS OF 2020, IT MUST BE A CHUNKED STREAM.
            # I REPEAT. IT MUST BE A CHUNKED STREAM.
            resp.stream = [f.getvalue()]

            resp.content_type = falcon.MEDIA_XML

            logger.debug("Responded with %s.", str(out_msg))
        except SyntaxError:
            raise falcon.HTTPBadRequest(description="Malformed XML.")

    def on_get(self, req, resp):
        data = """
        <html>
        <head>
            <title>Interstate Love Song</title>
            <style>
                body {
                    font-family: sans-serif;
                    height: 100%;
                    background: lightgray;
                    color: gray;
                }
                .container {
                    height: 100%;
                    display: flex;
                    align-items: center;
                    justify-content: center;
                }
                h1 {
                    font-size: 2em;
                }
                h2 {
                    position: relative;
                    top: 1.5em;
                    right: 1em;
                }
            </style>
        </head>
        <body>
            <div class="container">
                <h1>Interstate Love Song</h1>
                <h2>
                    v{version}
                </h2>
            </div>
        </body>
        </html>
        """.format(
            version=VERSION
        )

        resp.content_type = falcon.MEDIA_HTML

        resp.body = data


class FallbackSessionMiddleware(BeakerSessionMiddleware):
    """A work-around session handler for situation where the PCOIP-client doesn't set its cookies properly. You can then
    use this instead to track the session.

    .. note::
        The PCOIP-client sends a unique header for each session, we simply use this as our session ID.
    """

    HEADER_NAME = "CLIENT-LOG-ID"

    def process_request(self, request, *args):
        session_id = request.headers.get(FallbackSessionMiddleware.HEADER_NAME, None)
        session = SessionObject(request.env, id=session_id, **self.options)

        request.env[self.environ_key] = session

    def process_response(self, request, response, resource, request_succeded):
        session = request.env.get(self.environ_key, None)
        session.persist()

        if not session:
            return

        return super(FallbackSessionMiddleware, self).process_request(
            request, response, resource, request_succeded
        )


class CookieCaseFixedResponse(falcon.Response):
    """A Response type whose sole purpose is to set the case on "set-cookie" headers to the explicit case "Set-Cookie".

    This is because the Teradici PCOIP client REQUIRES this case for it to accept the cookie. Yeah don't ask me.
    """

    def _wsgi_headers(self, media_type=None, py2=compat.PY2):
        # Traverse the headers returned and just fixup those named "set-cookie".
        items = super()._wsgi_headers(media_type, py2)
        new_items = []
        for name, value in items:
            # Important to do a case insensitive match here, since it looks like future Falcon versions may preserve
            # case.
            if name.lower() == "set-cookie":
                name = "Set-Cookie"
            new_items.append((name, value))
        return new_items


def get_falcon_api(
    broker_resource: BrokerResource,
    settings: Settings = Settings(),
    use_fallback_sessions: bool = False,
) -> API:
    logging.basicConfig(level=settings.logging.level.value)

    beaker_settings = {
        "session.type": settings.beaker.type,
        "session.cookie_expires": True,
        "session.auto": True,  # We got to have this on as things are currently programmed.
        "session.key": "JSESSIONID",
        "session.secure": True,
        "session.httponly": True,
        "session.data_dir": settings.beaker.data_dir,
    }
    beaker_middleware = None
    if not use_fallback_sessions:
        beaker_middleware = BeakerSessionMiddleware(beaker_settings)
    else:
        beaker_middleware = FallbackSessionMiddleware(beaker_settings)

    api = API(middleware=beaker_middleware, response_type=CookieCaseFixedResponse)
    api.add_route("/pcoip-broker/xml", resource=broker_resource)

    return api
