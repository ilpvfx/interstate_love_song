from abc import ABC, abstractmethod
from pyexpat import ExpatError
from typing import Callable, Any, Optional
from xml.etree.ElementTree import ParseError, tostring

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
        self._request.env["beaker.session"] = data

    def get_data(self):
        return self._request.env["beaker.session"]


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

        try:
            xml = fromstring(req.bounded_stream.read())

            in_msg = self._deserialize(xml)

            new_session_data, out_msg = protocol(in_msg, session_setter.get_data())
            session_setter.set_data(new_session_data)

            resp.body = tostring(self._serialize(out_msg), encoding="unicode")
        except SyntaxError as e:
            raise falcon.HTTPBadRequest(description="Malformed XML.")


def get_falcon_api(broker_resource: BrokerResource) -> API:
    beaker_middleware = BeakerSessionMiddleware()

    api = API(middleware=beaker_middleware)
    api.add_route("/pcoip-broker/xml", resource=broker_resource)

    return api
