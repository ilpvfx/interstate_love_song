import logging
from dataclasses import dataclass, field
from enum import Enum
from typing import Sequence, Any, Tuple, Optional, Callable

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
)
from interstate_love_song._version import __version__

logger = logging.getLogger(__name__)

import socket


class ProtocolState(Enum):
    WAITING_FOR_HELLO = 0
    WAITING_FOR_AUTHENTICATE = 1
    WAITING_FOR_GETRESOURCELIST = 2
    WAITING_FOR_ALLOCATERESOURCE = 3
    WAITING_FOR_BYE = 4


@dataclass
class ProtocolSession:
    username: Optional[str] = None
    password: Optional[str] = None
    state: ProtocolState = ProtocolState.WAITING_FOR_HELLO
    resources: Sequence[Resource] = field(default_factory=lambda: [])


ProtocolAction = Tuple[Optional[ProtocolSession], Optional[Message]]
ProtocolHandler = Callable[[Message, Optional[ProtocolSession]], ProtocolAction]


def _assert_session_exist(s: Optional[ProtocolSession]):
    if s is None:
        raise ValueError("session was expected to be non-None. This is a bug.")


class BrokerProtocolHandler:
    """Implements the logical level of the broker protocol. It is implemented as a state machine where state
    transitions happen based on the values of the message and the broker session."""

    def __init__(self, mapper: Mapper):
        """
        :param mapper:
            A mapper to use for authentication and resource assignment.
        :raises ValueError:
        """
        if not isinstance(mapper, Mapper):
            raise ValueError("Expected a Mapper instance.")
        self._mapper = mapper

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
            ProtocolState.WAITING_FOR_BYE: (ByeRequest, self._bye),
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
        hostname = socket.gethostname()
        response = HelloResponse(hostname)
        # The PCOIP-client sends a hello with this as the product name to check if we are connecting to a broker
        # or to a machine. We want to stay in the WAITING_FOR_HELLO state in those cases.
        if msg.client_product_name == "QueryBrokerClient":
            return None, response
        else:
            return ProtocolSession(state=ProtocolState.WAITING_FOR_AUTHENTICATE), response

    def _authenticate(
        self, msg: AuthenticateRequest, session: Optional[ProtocolSession]
    ) -> ProtocolAction:
        _assert_session_exist(session)

        mapper_status, resources = self.mapper.map((msg.username, msg.password))
        if mapper_status == MapperStatus.SUCCESS:
            session.username = msg.username
            session.password = msg.password
            session.state = ProtocolState.WAITING_FOR_GETRESOURCELIST
            session.resources = resources
            return session, AuthenticateSuccessResponse()
        else:
            session.username = None
            session.password = None
            session.state = ProtocolState.WAITING_FOR_AUTHENTICATE
            session.resources = []
            return session, AuthenticateFailedResponse()

    def _get_resource_list(
        self, msg: GetResourceListRequest, session: Optional[ProtocolSession]
    ) -> ProtocolAction:
        _assert_session_exist(session)
        session.state = ProtocolState.WAITING_FOR_ALLOCATERESOURCE

        def teradicis():
            i = 0
            for resource in session.resources:
                yield TeradiciResource(resource.name, str(i))
                i += 1

        return session, GetResourceListResponse(list(teradicis()))

    def _allocate_resource(
        self, msg: AllocateResourceRequest, session: Optional[ProtocolSession]
    ) -> ProtocolAction:
        _assert_session_exist(session)

        session.state = ProtocolState.WAITING_FOR_BYE
        return (
            session,
            AllocateResourceSuccessResponse(
                ip_address="NO BUENO",
                hostname="NO BUENO",
                sni="NO BUENO",
                port=666,
                session_id="NO BUENO",
                connect_tag="NO BUENO",
                resource_id=1,
            ),
        )

    def _bye(self, msg: ByeRequest, session: Optional[ProtocolSession]) -> ProtocolAction:
        return None, ByeResponse()
