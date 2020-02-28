from abc import ABC, abstractmethod
from dataclasses import dataclass
from enum import Enum
from typing import Tuple, Optional, Sequence

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


MapperResult = Tuple[MapperStatus, Sequence[Resource]]


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
            a tuple of a MapperStatus and a sequence, the sequence shall be empty unless the status is SUCCESS.
        """
        pass
