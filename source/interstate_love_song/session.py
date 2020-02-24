from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Optional


class SessionError(Exception):
    pass
