import socket
import logging
from dataclasses import dataclass, field
from enum import Enum
from typing import Mapping, Sequence, Tuple, Optional, Callable

from interstate_love_song import agent
from interstate_love_song.agent import AllocateSessionStatus
from interstate_love_song.mapping import Mapper, Resource, MapperStatus
from interstate_love_song.transport import (
    Message,
    HelloRequest,
    AuthenticateRequest,
    HelloResponse,
    AuthenticateSuccessResponse,
    GetResourceListRequest,
    AllocateResourceRequest,
    GetResourceListResponse,
    AllocateResourceSuccessResponse,
    ByeRequest,
    ByeResponse,
    TeradiciResource,
    AuthenticateFailedResponse,
    AllocateResourceFailureResponse,
)

logger = logging.getLogger(__name__)


class ProtocolState(Enum):
    """The different states the protocol may find itself in. The error states are not represented, we just send an error
    response and either stay in a state or go to WAITING_FOR_HELLO.
    """

    WAITING_FOR_HELLO = 0
    WAITING_FOR_AUTHENTICATE = 1
    WAITING_FOR_GETRESOURCELIST = 2
    WAITING_FOR_ALLOCATERESOURCE = 3
    WAITING_FOR_BYE = 4


@dataclass
class ProtocolSession:
    """Holds state data for the protocol. The Protocol handler is stateless itself.
    """

    username: Optional[str] = None
    password: Optional[str] = None
    domain: Optional[str] = None
    state: ProtocolState = ProtocolState.WAITING_FOR_HELLO
    resources: Mapping[str, Resource] = field(default_factory=lambda: {})


ProtocolAction = Tuple[Optional[ProtocolSession], Optional[Message]]
ProtocolHandler = Callable[[Message, Optional[ProtocolSession]], ProtocolAction]


def _assert_session_exist(s: Optional[ProtocolSession]):
    if s is None:
        raise ValueError("session was expected to be non-None. This is a bug.")


class BrokerProtocolHandler:
    """Implements the logical level of the broker protocol. It is implemented as a state machine where state
    transitions happen based on the values of the message and the broker session.

    This means that the handler is completely stateless in itself, it only depends on inputs and is almost deterministic,
    the exceptions are:
        - when asked to allocate a resource, since it depends upon the answer from the Teradici resource.
        - the mapper may not be deterministic.
    """

    def __init__(self, mapper: Mapper, allocate_session=agent.allocate_session):
        """
        :param mapper:
            A mapper to use for authentication and resource assignment.
        :raises ValueError:
        """
        if not isinstance(mapper, Mapper):
            raise ValueError("Expected a Mapper instance.")
        if not callable(allocate_session):
            raise ValueError("Expected allocate_session to be a callable.")
        self._mapper = mapper
        self._allocate_session = allocate_session

    @property
    def mapper(self) -> Mapper:
        return self._mapper

    def __call__(self, msg: Message, session: Optional[ProtocolSession]) -> ProtocolAction:
        """Handles the message and returns the new state, session data and the response.

        :param msg:
            The message to handle.
        :param session:
            A slot that allows the protocol handler to register and read the session.

        :return: An optional session data and a response message. If a session is active but this returns
            None as the current session data, the session should be removed from store.
        """
        if not isinstance(msg, Message):
            raise ValueError("msg must inherit from Message.")
        if session is not None and not isinstance(session, ProtocolSession):
            raise ValueError("session must be either None or ProtocolSession.")

        msg_type = type(msg)

        # treat bye as a general abort
        if msg_type is ByeRequest:
            return None, ByeResponse()

        routing_table = {
            ProtocolState.WAITING_FOR_HELLO: (HelloRequest, self._hello),
            ProtocolState.WAITING_FOR_AUTHENTICATE: (AuthenticateRequest, self._authenticate),
            ProtocolState.WAITING_FOR_GETRESOURCELIST: (
                GetResourceListRequest,
                self._get_resource_list,
            ),
            ProtocolState.WAITING_FOR_ALLOCATERESOURCE: (
                AllocateResourceRequest,
                self._allocate_resource,
            ),
        }

        state = ProtocolState.WAITING_FOR_HELLO if session is None else session.state

        assert state in routing_table  # check that we have implemented this state.
        accepted_msg, handler = routing_table[state]

        if msg_type is accepted_msg:
            return handler(msg, session)
        else:
            logger.info(
                "Got an unexpected message (%s) for this state (%s), expected %s",
                str(msg_type),
                str(state),
                str(accepted_msg),
            )
            return None, None

    def _hello(self, msg: HelloRequest, session: Optional[ProtocolSession]) -> ProtocolAction:
        """We may get two hello messages in this situation.
        - A hello with the product name "QueryBrokerClient". The PCOIP-client sends this to check whether it's dealing
          directly with a machine or a broker.
        - A hello with the clients real product name, that's when we want our session to start.
        """
        hostname = socket.gethostname()
        response = HelloResponse(hostname, domains=self.mapper.domains)
        # The PCOIP-client sends a hello with this as the product name to check if we are connecting to a broker
        # or to a machine. We want to stay in the WAITING_FOR_HELLO state in those cases.
        if msg.client_product_name == "QueryBrokerClient":
            return None, response
        else:
            return ProtocolSession(state=ProtocolState.WAITING_FOR_AUTHENTICATE), response

    def _authenticate(
        self, msg: AuthenticateRequest, session: Optional[ProtocolSession]
    ) -> ProtocolAction:
        """We only expect authenticate messages here. When we get one, we ask the mapper to authenticate and return
        the assigned resources.

        If authentication fails, the PCOIP client may try again, so this may transition back to itself.
        """
        _assert_session_exist(session)

        mapper_status, resources = self.mapper.map((msg.username, msg.password))
        if mapper_status == MapperStatus.SUCCESS:
            session.username = msg.username
            session.password = msg.password
            session.domain = msg.domain

            session.state = ProtocolState.WAITING_FOR_GETRESOURCELIST
            session.resources = resources
            return session, AuthenticateSuccessResponse()
        else:
            session.username = None
            session.password = None
            session.state = ProtocolState.WAITING_FOR_AUTHENTICATE
            session.resources = {}
            return session, AuthenticateFailedResponse()

    def _get_resource_list(
        self, msg: GetResourceListRequest, session: Optional[ProtocolSession]
    ) -> ProtocolAction:
        """This means authentication was successful. We have already assigned resources, those are in the session, so we
        can just return those. We need to be careful with resource IDs.
        """
        _assert_session_exist(session)
        session.state = ProtocolState.WAITING_FOR_ALLOCATERESOURCE
        return (
            session,
            GetResourceListResponse(
                [
                    TeradiciResource(resource.name, resource_id)
                    for resource_id, resource in session.resources.items()
                ]
            ),
        )

    def _allocate_resource(
        self, msg: AllocateResourceRequest, session: Optional[ProtocolSession]
    ) -> ProtocolAction:
        """The client should now ask us to allocate a session on a chosen machine. So we need to communicate with the
        machine and obtain a session.
        """
        _assert_session_exist(session)

        hostname = session.resources[msg.resource_id].hostname
        status, agent_session = self._allocate_session(
            msg.resource_id, hostname, session.username, session.password, session.domain
        )

        if status == AllocateSessionStatus.SUCCESSFUL:
            session.state = ProtocolState.WAITING_FOR_BYE

            return (
                session,
                AllocateResourceSuccessResponse(
                    ip_address=agent_session.ip_address,
                    hostname=hostname,
                    sni=agent_session.sni,
                    port=agent_session.port,
                    session_id=agent_session.session_id,
                    connect_tag=agent_session.session_tag,
                    resource_id=agent_session.resource_id,
                ),
            )
        else:
            result_id = "FAILED_USER_AUTH"
            if status == AllocateSessionStatus.FAILED_ANOTHER_SESSION_STARTED:
                result_id = "FAILED_ANOTHER_SESION_STARTED"
            return session, AllocateResourceFailureResponse(result_id=result_id)
