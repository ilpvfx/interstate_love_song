import logging
from abc import ABC, abstractmethod
from io import BytesIO

from pyexpat import ExpatError
from typing import Callable, Any, Optional
from xml.etree.ElementTree import ParseError, tostring, ElementTree

import falcon
from defusedxml.ElementTree import fromstring
from falcon import API
from falcon_middleware_beaker import BeakerSessionMiddleware
from .protocol import (
    ProtocolState,
    ProtocolAction,
    ProtocolHandler,
    ProtocolSession,
    BrokerProtocolHandler,
)
from .serialization import serialize_message, deserialize_message, HelloRequest

ProtocolCreator = Callable[[], ProtocolHandler]

logger = logging.getLogger(__name__)
logger.setLevel("INFO")


def standard_protocol_creator():
    return BrokerProtocolHandler()


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
        protocol_creator: ProtocolCreator = standard_protocol_creator,
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
        print(req.cookies)

        try:
            xml_str = req.bounded_stream.read()
            logger.info("Got XML: %s", str(xml_str))
            xml = fromstring(xml_str)

            in_msg = self._deserialize(xml)

            logger.info("Received POST: Message: %s.", str(in_msg))

            new_session_data, out_msg = protocol(in_msg, session_setter.get_data())
            session_setter.set_data(new_session_data)

            f = BytesIO()
            ElementTree(self._serialize(out_msg)).write(f, encoding="utf-8", xml_declaration=True)

            # WE MUST RETURN A CHUNKED STREAM, OR TERADICI WILL BE VERY UNHAPPY.
            # DON'T JUST CHANGE THIS TO resp.body = blabla, AS OF 2020, IT MUST BE A CHUNKED STREAM.
            # I REPEAT. IT MUST BE A CHUNKED STREAM.
            resp.stream = [f.getvalue()]

            resp.content_type = falcon.MEDIA_XML

            logger.info("Responded with %s.", str(out_msg))
        except SyntaxError as e:
            raise falcon.HTTPBadRequest(description="Malformed XML.")


def get_falcon_api(broker_resource: BrokerResource) -> API:
    beaker_middleware = BeakerSessionMiddleware(
        {
            "session.type": "file",
            "session.cookie_expires": True,
            "session.auto": True,  # We got to have this on as things are currently programmed.
            "session.key": "JSESSIONID",
            "session.secure": True,
            "session.httponly": True,
            "session.data_dir": "C:\\",
        }
    )

    api = API(middleware=beaker_middleware)
    api.add_route("/pcoip-broker/xml", resource=broker_resource)

    return api
