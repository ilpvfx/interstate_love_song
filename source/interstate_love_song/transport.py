from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Sequence
from ._version import __version__


class Message:
    pass


@dataclass
class HelloRequest(Message):
    """Represents the Hello message set by PCOIP-client to the broker."""

    pass


@dataclass
class HelloResponse(Message):
    """Represents the answer to the HelloRequest, from the broker to the PCOIP-client.

    It tells the PCOIP-client about the authentication modes.
    """

    hostname: str
    product_name: str = "Interstate Love Song"
    product_version: str = __version__
    platform: str = "linux"
    locale: str = "en_US"
    ip_address: str = "N/A"
    authentication_methods: Sequence[str] = field(
        default_factory=lambda: ["AUTHENTICATE_VIA_PASSWORD"]
    )


@dataclass
class AuthenticateRequest(Message):
    """Represents the Authenticate message sent by the PCOIP-client.

    It tells the broker to authenticate the user with the given credentials.
    """

    username: str
    password: str


@dataclass
class AuthenticateSuccessResponse(Message):
    """Represents the answer to the AuthenticateRequest, from the broker to the PCOIP-client, if a success"""

    pass


@dataclass
class AuthenticateFailedResponse(Message):
    """Represents the answer to the AuthenticateRequest, from the broker to the PCOIP-client, if a failure"""

    pass


@dataclass
class GetResourceListRequest(Message):
    """Represents a request to the broker from the PCOIP-client, asking it to return a list of Teradici 'machines' that
    the user may chose to connecct to."""

    pass


@dataclass
class TeradiciResource:
    resource_name: str
    resource_id: str
    resource_type: str = "DESKTOP"
    session_type: str = "VDI"
    resource_state: str = "UNKNOWN"
    protocol: str = "PCOIP"


@dataclass
class GetResourceListResponse(Message):
    """The brokers answer to a GetResourceListRequest. It's more or less just the list of available resources, if any.
    """

    resources: Sequence[TeradiciResource] = field(default_factory=lambda: [])


@dataclass
class AllocateResourceRequest(Message):
    """The PCOIP-client has chosen a resource and asks the broker to allocate it for us. The broker must then ask the
    resource for a session id, and answer with it."""

    pass


@dataclass
class AllocateResourceSuccessResponse(Message):
    """After asking a resource for a session id, responds to the PCOIP-client with the session id and assorted data.
    """

    ip_address: str
    hostname: str
    sni: str
    port: int
    session_id: str
    connect_tag: str
    resource_id: str = "DOESNT MATTER"
    protocol: str = "PCOIP"


@dataclass
class BadMessage(Message):
    """Signifies a message that couldn't be decoded or was improper somehow."""

    pass


class MessageEncodingError(Exception):
    pass