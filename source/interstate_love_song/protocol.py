from dataclasses import dataclass, field
from enum import Enum
from typing import Sequence, Any, Tuple, Optional, Callable

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
)
from interstate_love_song._version import __version__

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


ProtocolAction = Tuple[Optional[ProtocolSession], Optional[Message]]
ProtocolHandler = Callable[[Message, Optional[ProtocolSession]], ProtocolAction]


def _assert_session_exist(s: Optional[ProtocolSession]):
    if s is None:
        raise ValueError("session was expected to be non-None. This is a bug.")


class BrokerProtocolHandler:
    """Implements the logical level of the broker protocol. It is implemented as a state machine where state
    transitions happen based on the values of the message and the broker session."""

    def __init__(self):
        pass

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
            raise ValueError("session must be either None or BrokerSessionData.")

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
            return None, None

    def _hello(self, msg: HelloRequest, session: Optional[ProtocolSession]) -> ProtocolAction:
        hostname = socket.gethostname()
        return (
            ProtocolSession(state=ProtocolState.WAITING_FOR_AUTHENTICATE),
            HelloResponse(hostname),
        )

    def _authenticate(
        self, msg: AuthenticateRequest, session: Optional[ProtocolSession]
    ) -> ProtocolAction:
        _assert_session_exist(session)
        # TODO: Do better auth here.
        session.username = msg.username
        session.password = msg.password
        session.state = ProtocolState.WAITING_FOR_GETRESOURCELIST
        return session, AuthenticateSuccessResponse()

    def _get_resource_list(
        self, msg: GetResourceListRequest, session: Optional[ProtocolSession]
    ) -> ProtocolAction:
        _assert_session_exist(session)
        session.state = ProtocolState.WAITING_FOR_ALLOCATERESOURCE
        return session, GetResourceListResponse([])

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
