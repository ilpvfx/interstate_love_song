import socket
from dataclasses import dataclass
from typing import Optional

import pytest

from interstate_love_song.agent import AgentSession, AllocateSessionStatus
from interstate_love_song.mapping import Mapper, Credentials, MapperResult, MapperStatus, Resource
from interstate_love_song.protocol import BrokerProtocolHandler, ProtocolState, ProtocolSession
from interstate_love_song.transport import *


class DummyMapper(Mapper):
    @property
    def name(self):
        return "DummyMapper"

    @property
    def domains(self):
        return ['example.com']

    @classmethod
    def create_from_settings(cls, settings):
        return cls()

    def __init__(self, username="test", password="test", resources=[], domain="example.com"):
        super().__init__()
        self.username = username
        self.password = password
        self.resources = resources
        self.domain = domain
        self.map_called = False

    def map(self, credentials: Credentials, previous_host: Optional[str] = None) -> MapperResult:
        self.map_called = True
        usr, psw = credentials
        if usr == self.username and psw == self.password:
            if not self.resources:
                return MapperStatus.NO_MACHINE, {}
            else:
                return MapperStatus.SUCCESS, dict((str(k), v) for k, v in enumerate(self.resources))
        else:
            return MapperStatus.AUTHENTICATION_FAILED, {}


@dataclass
class Fixture:
    mapper: DummyMapper = DummyMapper("user", "pass", [], 'example.com')


@pytest.fixture
def ctx() -> Fixture:
    return Fixture()


def test_broker_protocol_handler_constructor(ctx: Fixture):
    with pytest.raises(ValueError):
        BrokerProtocolHandler(123)

    bph = BrokerProtocolHandler(ctx.mapper)
    assert bph.mapper is ctx.mapper


def test_broker_protocol_handler_call_invalid_message(ctx: Fixture):
    bph = BrokerProtocolHandler(ctx.mapper)

    with pytest.raises(ValueError):
        bph(None, None)


def test_broker_protocol_handler_call_waiting_for_hello_hello(ctx: Fixture):
    bph = BrokerProtocolHandler(ctx.mapper)

    session_data, response = bph(
        HelloRequest(client_hostname="Lagrange", client_product_name="Abel"), None
    )
    assert session_data.state == ProtocolState.WAITING_FOR_AUTHENTICATE

    assert isinstance(response, HelloResponse)
    assert response.hostname == socket.gethostname()
    assert "AUTHENTICATE_VIA_PASSWORD" in response.authentication_methods

    assert isinstance(session_data, ProtocolSession)
    assert session_data.username is None
    assert session_data.password is None


def test_broker_protocol_handler_call_waiting_for_hello_hello_query_broker_client(ctx: Fixture):
    bph = BrokerProtocolHandler(ctx.mapper)

    session_data, response = bph(
        HelloRequest(client_hostname="Lagrange", client_product_name="QueryBrokerClient"), None
    )

    assert isinstance(response, HelloResponse)
    assert response.hostname == socket.gethostname()
    assert "AUTHENTICATE_VIA_PASSWORD" in response.authentication_methods

    assert session_data is None


def test_broker_protocol_handler_call_waiting_for_hello_bye(ctx: Fixture):
    bph = BrokerProtocolHandler(ctx.mapper)
    session_data, response = bph(
        ByeRequest(), ProtocolSession(state=ProtocolState.WAITING_FOR_HELLO)
    )

    assert isinstance(response, ByeResponse)

    assert session_data is None


def test_broker_protocol_handler_call_waiting_for_hello_other_message(ctx: Fixture):
    bph = BrokerProtocolHandler(ctx.mapper)

    session_data, response = bph(
        AuthenticateRequest("Leonhard", "Euler", "example.com"),
        ProtocolSession(state=ProtocolState.WAITING_FOR_HELLO),
    )

    assert response is None

    assert session_data is None


def test_broker_protocol_handler_call_waiting_for_authenticate_authenticate_success(ctx: Fixture):
    bph = BrokerProtocolHandler(ctx.mapper)

    ctx.mapper.resources = [Resource("Kurt", "Gödel")]

    session_data, response = bph(
        AuthenticateRequest(ctx.mapper.username, ctx.mapper.password, ctx.mapper.domain,),
        ProtocolSession(state=ProtocolState.WAITING_FOR_AUTHENTICATE),
    )

    assert session_data.state == ProtocolState.WAITING_FOR_GETRESOURCELIST

    assert isinstance(response, AuthenticateSuccessResponse)

    assert isinstance(session_data, ProtocolSession)
    assert session_data.username == ctx.mapper.username
    assert session_data.password == ctx.mapper.password
    assert list(session_data.resources.values()) == ctx.mapper.resources

    assert ctx.mapper.map_called is True


def test_broker_protocol_handler_call_waiting_for_authenticate_authenticate_no_resources(
    ctx: Fixture,
):
    bph = BrokerProtocolHandler(ctx.mapper)

    ctx.mapper.resources = []

    session_data, response = bph(
        AuthenticateRequest(ctx.mapper.username, ctx.mapper.password, ctx.mapper.domain),
        ProtocolSession(state=ProtocolState.WAITING_FOR_AUTHENTICATE),
    )

    assert session_data.state == ProtocolState.WAITING_FOR_AUTHENTICATE

    # In this case, authentication should be successful but there are no machines, so we have to fail
    # anyway, and not set the session data.
    assert isinstance(response, AuthenticateFailedResponse)

    assert isinstance(session_data, ProtocolSession)
    assert session_data.username is None
    assert session_data.password is None
    assert list(session_data.resources) == []

    assert ctx.mapper.map_called is True


def test_broker_protocol_handler_call_waiting_for_authenticate_authenticate_failed(ctx: Fixture):
    bph = BrokerProtocolHandler(ctx.mapper)

    ctx.mapper.resources = {"0": Resource("Kurt", "Gödel")}

    session_data, response = bph(
        AuthenticateRequest(ctx.mapper.username, ctx.mapper.password + "wrong", ctx.mapper.domain),
        ProtocolSession(state=ProtocolState.WAITING_FOR_AUTHENTICATE),
    )

    assert session_data.state == ProtocolState.WAITING_FOR_AUTHENTICATE

    assert isinstance(response, AuthenticateFailedResponse)

    assert isinstance(session_data, ProtocolSession)
    # The authentication failed so we shouldn't set these.
    assert session_data.username is None
    assert session_data.password is None
    assert list(session_data.resources) == []

    assert ctx.mapper.map_called is True


def test_broker_protocol_handler_call_waiting_for_authenticate_bye(ctx: Fixture):
    bph = BrokerProtocolHandler(ctx.mapper)
    session_data, response = bph(
        ByeRequest(), ProtocolSession(state=ProtocolState.WAITING_FOR_AUTHENTICATE)
    )

    assert isinstance(response, ByeResponse)

    assert session_data is None


def test_broker_protocol_handler_call_waiting_for_authenticate_other_message(ctx: Fixture):
    bph = BrokerProtocolHandler(ctx.mapper)
    session_data, response = bph(
        HelloRequest(client_hostname="Euler", client_product_name="Abel"),
        ProtocolSession(state=ProtocolState.WAITING_FOR_AUTHENTICATE),
    )

    assert response is None

    assert session_data is None


def test_broker_protocol_handler_call_waiting_for_getresourcelist_getresourcelist(ctx: Fixture):
    bph = BrokerProtocolHandler(ctx.mapper)

    resources = {"0": Resource("Kurt", "Gödel"), "1": Resource("Paul", "Dirac")}

    session_data, response = bph(
        GetResourceListRequest(),
        ProtocolSession(
            "Leonhard",
            "Euler",
            state=ProtocolState.WAITING_FOR_GETRESOURCELIST,
            resources=resources,
        ),
    )

    assert session_data.state == ProtocolState.WAITING_FOR_ALLOCATERESOURCE
    # print(response)
    assert isinstance(response, GetResourceListResponse)
    assert len(response.resources) == len(resources)
    assert response.resources[0].resource_name == resources["0"].name
    assert response.resources[0].resource_id == "0"
    assert response.resources[1].resource_name == resources["1"].name
    assert response.resources[1].resource_id == "1"

    assert isinstance(session_data, ProtocolSession)
    assert session_data.username == "Leonhard"
    assert session_data.password == "Euler"
    assert session_data.resources == resources


def test_broker_protocol_handler_call_waiting_for_allocateresource_allocateresource_success(
    ctx: Fixture,
):
    agent_session = AgentSession("kolmogorov", "kolmogorov.edu", 666, "Catmull", "Rom", "0")

    def allocate_session(*args, **kwargs):
        return AllocateSessionStatus.SUCCESSFUL, agent_session

    protocol_session = ProtocolSession(
        "Leonhard",
        "Euler",
        state=ProtocolState.WAITING_FOR_ALLOCATERESOURCE,
        resources=[Resource("Hilbert", "hilbert.gov")],
    )

    bph = BrokerProtocolHandler(ctx.mapper, allocate_session=allocate_session)

    session_data, response = bph(AllocateResourceRequest(resource_id=0), protocol_session)

    assert isinstance(response, AllocateResourceSuccessResponse)
    assert response.sni == agent_session.sni
    assert response.port == agent_session.port
    assert response.session_id == agent_session.session_id
    assert response.connect_tag == agent_session.session_tag
    assert response.protocol == "PCOIP"

    assert session_data is not None
    assert session_data.state == ProtocolState.WAITING_FOR_BYE


def test_broker_protocol_handler_call_waiting_for_allocateresource_allocateresource_failure_to_connect(
    ctx: Fixture,
):
    def allocate_session(*args, **kwargs):
        return AllocateSessionStatus.CONNECTION_ERROR, None

    protocol_session = ProtocolSession(
        "Leonhard",
        "Euler",
        state=ProtocolState.WAITING_FOR_ALLOCATERESOURCE,
        resources={"0": Resource("Hilbert", "hilbert.gov")},
    )

    bph = BrokerProtocolHandler(ctx.mapper, allocate_session=allocate_session)

    session_data, response = bph(AllocateResourceRequest(resource_id="0"), protocol_session)

    assert isinstance(response, AllocateResourceFailureResponse)
    # TODO: We should use the proper response here.
    assert response.result_id == "FAILED_USER_AUTH"

    assert session_data is not None
    assert session_data.state == ProtocolState.WAITING_FOR_ALLOCATERESOURCE


def test_broker_protocol_handler_call_waiting_for_allocateresource_allocateresource_failure_to_auth(
    ctx: Fixture,
):
    def allocate_session(*args, **kwargs):
        return AllocateSessionStatus.FAILED_USER_AUTH, None

    protocol_session = ProtocolSession(
        "Leonhard",
        "Euler",
        state=ProtocolState.WAITING_FOR_ALLOCATERESOURCE,
        resources={"0": Resource("Hilbert", "hilbert.gov")},
    )

    bph = BrokerProtocolHandler(ctx.mapper, allocate_session=allocate_session)

    session_data, response = bph(AllocateResourceRequest(resource_id="0"), protocol_session)

    assert isinstance(response, AllocateResourceFailureResponse)
    assert response.result_id == "FAILED_USER_AUTH"

    assert session_data is not None
    assert session_data.state == ProtocolState.WAITING_FOR_ALLOCATERESOURCE


def test_broker_protocol_handler_call_waiting_for_allocateresource_allocateresource_session_in_use(
    ctx: Fixture,
):
    def allocate_session(*args, **kwargs):
        return AllocateSessionStatus.FAILED_ANOTHER_SESSION_STARTED, None

    protocol_session = ProtocolSession(
        "Leonhard",
        "Euler",
        state=ProtocolState.WAITING_FOR_ALLOCATERESOURCE,
        resources={"0": Resource("Hilbert", "hilbert.gov")},
    )

    bph = BrokerProtocolHandler(ctx.mapper, allocate_session=allocate_session)

    session_data, response = bph(AllocateResourceRequest(resource_id="0"), protocol_session)

    assert isinstance(response, AllocateResourceFailureResponse)
    assert response.result_id == "FAILED_ANOTHER_SESION_STARTED"

    assert session_data is not None
    assert session_data.state == ProtocolState.WAITING_FOR_ALLOCATERESOURCE


def test_broker_protocol_handler_call_waiting_for_bye_bye(ctx: Fixture):
    bph = BrokerProtocolHandler(ctx.mapper)

    session_data, response = bph(ByeRequest(), ProtocolSession(state=ProtocolState.WAITING_FOR_BYE))

    assert session_data is None
    assert isinstance(response, ByeResponse)
