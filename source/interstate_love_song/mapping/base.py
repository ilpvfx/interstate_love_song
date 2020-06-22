from abc import ABC, abstractmethod
from dataclasses import dataclass
from enum import Enum
from typing import Tuple, Optional, Sequence, Any, Mapping
from ..agent import allocate_session

Credentials = Tuple[str, str]


class MapperStatus(Enum):
    AUTHENTICATION_FAILED = 0
    NO_MACHINE = 1
    RESOURCE_UNRESPONSIVE = 2
    INTERNAL_ERROR = 3
    SUCCESS = 4


@dataclass
class Resource:
    """Represents a Resource (a Teradici "machine") that the user may connect to."""

    name: str
    hostname: str


MapperResult = Tuple[MapperStatus, Mapping[str, Resource]]


class Mapper(ABC):
    """A mapper specifies the strategy to use when assigning hosts/machines/resources to a particular user."""

    def __init__(self):
        pass

    @abstractmethod
    def map(self, credentials: Credentials, previous_host: Optional[str] = None) -> MapperResult:
        """Maps the user credentials to a set of hosts.

        :param credentials: The username and password.
        :param previous_host: A previous host for this user, if any.

        :raises TypeError:
            credentials could not be unpacked into two values.
        :returns:
            a tuple of a MapperStatus and a dict, the dict shall be empty unless the status is SUCCESS.
        """
        pass

    def allocate_session(self, *args, **kwargs):
        """This adds the ability for plugin mappers to intercept the call to `agent.allocate_session`"""
        return allocate_session(*args, **kwargs)

    @property
    @abstractmethod
    def domains():
        """Return a list of supported domains"""
        pass

    @property
    @abstractmethod
    def name(self):
        """The name of this mapper."""
        pass

    @classmethod
    def create_from_dict(cls, data: Mapping[str, Any]):
        """Create a new instance from settings"""
        return cls()
