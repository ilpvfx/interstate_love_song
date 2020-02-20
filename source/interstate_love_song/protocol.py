from dataclasses import dataclass, field
from enum import Enum
from typing import Sequence, Any, Tuple, Optional

from interstate_love_song.session import BrokerSessionData
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
)
from interstate_love_song._version import __version__

import socket


class ProtocolState(Enum):
    WAITING_FOR_HELLO = 0
    WAITING_FOR_AUTHENTICATE = 1
    WAITING_FOR_GETRESOURCELIST = 2
    WAITING_FOR_ALLOCATERESOURCE = 3
    TERMINATE = 100


ProtocolAction = Tuple[ProtocolState, Optional[BrokerSessionData], Optional[Message]]


def _assert_session_exist(s: Optional[BrokerSessionData]):
    if s is None:
        raise ValueError("session was expected to be non-None. This is a bug.")


class BrokerProtocolHandler:
    """Implements the logical level of the broker protocol. It is implemented as a state machine where state
    transitions happen based on the values of the message and the broker session."""

    def __init__(self, current_state: ProtocolState = ProtocolState.WAITING_FOR_HELLO):
        """Initialize the handler in the given state.

        :raises ValueError:
            current_state is not a ProtocolState. transport is not of type BrokerTransport.
        """
        if not isinstance(current_state, ProtocolState):
            raise ValueError("current_state must be a ProtocolState enum member.")
        self._state = current_state

    def __call__(self, msg: Message, session: Optional[BrokerSessionData]) -> ProtocolAction:
        """Handles the message and returns the new state, session data and the response.

        :param msg:
            The message to handle.
        :param session:
            A slot that allows the protocol handler to register and read the session.
        :rtype: ProtocolState
        :return: A new state, an optional session data and a response message. If a session is active but this returns
            None as the current session data, the session should be removed from store.
        """
        if not isinstance(msg, Message):
            raise ValueError("msg must inherit from Message.")
        if session is not None and not isinstance(session, BrokerSessionData):
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
        }

        assert self._state in routing_table  # check that we have implemented this state.
        accepted_msg, handler = routing_table[self._state]

        if msg_type is accepted_msg:
            return handler(msg, session)
        else:
            return ProtocolState.TERMINATE, None, None

    def _hello(self, msg: HelloRequest, session: Optional[BrokerSessionData]) -> ProtocolAction:
        hostname = socket.gethostname()
        return ProtocolState.WAITING_FOR_AUTHENTICATE, BrokerSessionData(), HelloResponse(hostname)

    def _authenticate(
        self, msg: AuthenticateRequest, session: Optional[BrokerSessionData]
    ) -> ProtocolAction:
        _assert_session_exist(session)
        # TODO: Do better auth here.
        session.username = msg.username
        session.password = msg.password
        return ProtocolState.WAITING_FOR_GETRESOURCELIST, session, AuthenticateSuccessResponse()

    def _get_resource_list(
        self, msg: GetResourceListRequest, session: Optional[BrokerSessionData]
    ) -> ProtocolAction:
        _assert_session_exist(session)

        return ProtocolState.WAITING_FOR_ALLOCATERESOURCE, session, GetResourceListResponse([])

    def _allocate_resource(
        self, msg: AllocateResourceRequest, session: Optional[BrokerSessionData]
    ) -> ProtocolAction:
        _assert_session_exist(session)

        return (
            ProtocolState.TERMINATE,
            None,
            AllocateResourceSuccessResponse(
                ip_address="NO BUENO",
                hostname="NO BUENO",
                sni="NO BUENO",
                port=666,
                session_id="NO BUENO",
                connect_tag="NO BUENO",
            ),
        )
