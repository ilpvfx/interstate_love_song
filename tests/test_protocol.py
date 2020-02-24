import socket
from dataclasses import dataclass

import pytest

from interstate_love_song.protocol import BrokerProtocolHandler, ProtocolState, ProtocolSession
from interstate_love_song.transport import *


@dataclass
class Fixture:
    pass


@pytest.fixture
def ctx() -> Fixture:
    return Fixture()


def test_broker_protocol_handler_call_invalid_message(ctx: Fixture):
    bph = BrokerProtocolHandler()

    with pytest.raises(ValueError):
        bph(None, None)


def test_broker_protocol_handler_call_waiting_for_hello_hello(ctx: Fixture):
    bph = BrokerProtocolHandler()

    session_data, response = bph(HelloRequest(client_hostname="Lagrange"), None)
    assert session_data.state == ProtocolState.WAITING_FOR_AUTHENTICATE

    assert isinstance(response, HelloResponse)
    assert response.hostname == socket.gethostname()
    assert "AUTHENTICATE_VIA_PASSWORD" in response.authentication_methods

    assert isinstance(session_data, ProtocolSession)
    assert session_data.username is None
    assert session_data.password is None


def test_broker_protocol_handler_call_waiting_for_hello_other_message(ctx: Fixture):
    bph = BrokerProtocolHandler()

    session_data, response = bph(
        AuthenticateRequest("Leonhard", "Euler"),
        ProtocolSession(state=ProtocolState.WAITING_FOR_HELLO),
    )

    assert response is None

    assert session_data is None


def test_broker_protocol_handler_call_waiting_for_authenticate_authenticate(ctx: Fixture):
    bph = BrokerProtocolHandler()

    session_data, response = bph(
        AuthenticateRequest("Leonhard", "Euler"),
        ProtocolSession(state=ProtocolState.WAITING_FOR_AUTHENTICATE),
    )

    assert session_data.state == ProtocolState.WAITING_FOR_GETRESOURCELIST

    assert isinstance(response, AuthenticateSuccessResponse)

    assert isinstance(session_data, ProtocolSession)
    assert session_data.username == "Leonhard"
    assert session_data.password == "Euler"


def test_broker_protocol_handler_call_waiting_for_authenticate_other_message(ctx: Fixture):
    bph = BrokerProtocolHandler()
    session_data, response = bph(
        HelloRequest(client_hostname="Euler"),
        ProtocolSession(state=ProtocolState.WAITING_FOR_AUTHENTICATE),
    )

    assert response is None

    assert session_data is None


def test_broker_protocol_handler_call_waiting_for_getresourcelist_getresourcelist(ctx: Fixture):
    bph = BrokerProtocolHandler()

    session_data, response = bph(
        GetResourceListRequest(),
        ProtocolSession("Leonhard", "Euler", state=ProtocolState.WAITING_FOR_GETRESOURCELIST),
    )

    assert session_data.state == ProtocolState.WAITING_FOR_ALLOCATERESOURCE

    assert isinstance(response, GetResourceListResponse)
    assert response.resources.count(0) == 0

    assert isinstance(session_data, ProtocolSession)
    assert session_data.username == "Leonhard"
    assert session_data.password == "Euler"


def test_broker_protocol_handler_call_waiting_for_allocateresource_allocateresource(ctx: Fixture):
    bph = BrokerProtocolHandler()

    session_data, response = bph(
        AllocateResourceRequest(resource_id=1),
        ProtocolSession("Leonhard", "Euler", state=ProtocolState.WAITING_FOR_ALLOCATERESOURCE),
    )

    # TODO: test asking the Teradici machines for a session etc.

    assert isinstance(response, AllocateResourceSuccessResponse)
    assert response.hostname == "NO BUENO"
    assert response.sni == "NO BUENO"
    assert response.port == 666
    assert response.session_id == "NO BUENO"
    assert response.connect_tag == "NO BUENO"
    assert response.protocol == "PCOIP"

    assert session_data is not None
    assert session_data.state == ProtocolState.WAITING_FOR_BYE


def test_broker_protocol_handler_call_waiting_for_bye_bye(ctx: Fixture):
    bph = BrokerProtocolHandler()

    session_data, response = bph(ByeRequest(), ProtocolSession(state=ProtocolState.WAITING_FOR_BYE))

    assert session_data is None
    assert isinstance(response, ByeResponse)
