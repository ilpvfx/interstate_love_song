import socket
from dataclasses import dataclass

import pytest

from interstate_love_song.protocol import BrokerProtocolHandler, ProtocolState
from interstate_love_song.session import BrokerSessionData
from interstate_love_song.transport import *


@dataclass
class Fixture:
    pass


@pytest.fixture
def ctx() -> Fixture:
    return Fixture()


def test_broker_protocol_handler_constructor(ctx: Fixture):
    with pytest.raises(ValueError):
        BrokerProtocolHandler(None)

    bph = BrokerProtocolHandler(ProtocolState.WAITING_FOR_HELLO)


def test_broker_protocol_handler_call_invalid_message(ctx: Fixture):
    bph = BrokerProtocolHandler()

    with pytest.raises(ValueError):
        bph(None, None)


def test_broker_protocol_handler_call_waiting_for_hello_hello(ctx: Fixture):
    bph = BrokerProtocolHandler(current_state=ProtocolState.WAITING_FOR_HELLO)

    new_state, session_data, response = bph(HelloRequest(client_hostname="Lagrange"), None)
    assert new_state == ProtocolState.WAITING_FOR_AUTHENTICATE

    assert isinstance(response, HelloResponse)
    assert response.hostname == socket.gethostname()
    assert "AUTHENTICATE_VIA_PASSWORD" in response.authentication_methods

    assert isinstance(session_data, BrokerSessionData)
    assert session_data.username is None
    assert session_data.password is None


def test_broker_protocol_handler_call_waiting_for_hello_other_message(ctx: Fixture):
    bph = BrokerProtocolHandler(current_state=ProtocolState.WAITING_FOR_HELLO)

    new_state, session_data, response = bph(
        AuthenticateRequest("Leonhard", "Euler"), BrokerSessionData()
    )
    assert new_state == ProtocolState.TERMINATE

    assert response is None

    assert session_data is None


def test_broker_protocol_handler_call_waiting_for_authenticate_authenticate(ctx: Fixture):
    bph = BrokerProtocolHandler(current_state=ProtocolState.WAITING_FOR_AUTHENTICATE)

    new_state, session_data, response = bph(
        AuthenticateRequest("Leonhard", "Euler"), BrokerSessionData()
    )

    assert new_state == ProtocolState.WAITING_FOR_GETRESOURCELIST

    assert isinstance(response, AuthenticateSuccessResponse)

    assert isinstance(session_data, BrokerSessionData)
    assert session_data.username == "Leonhard"
    assert session_data.password == "Euler"


def test_broker_protocol_handler_call_waiting_for_authenticate_other_message(ctx: Fixture):
    bph = BrokerProtocolHandler(current_state=ProtocolState.WAITING_FOR_AUTHENTICATE)
    new_state, session_data, response = bph(
        HelloRequest(client_hostname="Euler"), BrokerSessionData()
    )
    assert new_state == ProtocolState.TERMINATE

    assert response is None

    assert session_data is None


def test_broker_protocol_handler_call_waiting_for_getresourcelist_getresourcelist(ctx: Fixture):
    bph = BrokerProtocolHandler(current_state=ProtocolState.WAITING_FOR_GETRESOURCELIST)

    new_state, session_data, response = bph(
        GetResourceListRequest(), BrokerSessionData("Leonhard", "Euler")
    )

    assert new_state == ProtocolState.WAITING_FOR_ALLOCATERESOURCE

    assert isinstance(response, GetResourceListResponse)
    assert response.resources.count(0) == 0

    assert isinstance(session_data, BrokerSessionData)
    assert session_data.username == "Leonhard"
    assert session_data.password == "Euler"


def test_broker_protocol_handler_call_waiting_for_allocateresource_allocateresource(ctx: Fixture):
    bph = BrokerProtocolHandler(current_state=ProtocolState.WAITING_FOR_ALLOCATERESOURCE)

    new_state, session_data, response = bph(
        AllocateResourceRequest(resource_id=1), BrokerSessionData("Leonhard", "Euler")
    )

    assert new_state == ProtocolState.TERMINATE

    # TODO: test asking the Teradici machines for a session etc.

    assert isinstance(response, AllocateResourceSuccessResponse)
    assert response.hostname == "NO BUENO"
    assert response.sni == "NO BUENO"
    assert response.port == 666
    assert response.session_id == "NO BUENO"
    assert response.connect_tag == "NO BUENO"
    assert response.protocol == "PCOIP"

    assert session_data is None
