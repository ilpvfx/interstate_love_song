from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Optional


class SessionError(Exception):
    pass


@dataclass
class BrokerSessionData:
    username: Optional[str] = None
    password: Optional[str] = None
