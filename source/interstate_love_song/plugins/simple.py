import dataclasses
import argparse

from hashlib import pbkdf2_hmac
from typing import Mapping, Any

from interstate_love_song.mapping.base import *


def hash_pass(s: str, salt="IGNORED"):
    """Hash a password.

    Not the best way to store a password since the salt is known, but it offers a bit more protection than storing it
    plaintext."""
    return pbkdf2_hmac("sha256", s.encode("utf-8"), salt.encode("utf-8"), 100000).hex()


@dataclass
class SimpleMapperSettings:
    username: str = "test"
    password_hash: str = "change_me"
    resources: Sequence[Resource] = dataclasses.field(default_factory=lambda: [])


class SimpleMapper(Mapper):
    """A very simple mapper that accepts one set of credentials and returns a given set of resources."""

    def __init__(self, username: str, password_hash: str, resources: Sequence[Resource]):
        """

        :param username:
            The username to accept.
        :param password_hash:
            A password hash, output from hash_pass.
        :param resources:
        :raises TypeError:
        """
        super().__init__()
        self._username = str(username)
        self._password_hash = str(password_hash)
        self._resources = list(resources)

    @property
    def username(self) -> str:
        return self._username

    @property
    def password_hash(self) -> str:
        return self._password_hash

    @property
    def resources(self) -> Sequence[Resource]:
        return self._resources

    def map(self, credentials: Credentials, previous_host: Optional[str] = None) -> MapperResult:
        usr, psw = credentials
        if not isinstance(usr, str) or not isinstance(psw, str):
            raise ValueError("username and password must be strings.")

        if usr == self.username and hash_pass(psw) == self._password_hash:
            if self._resources:
                return MapperStatus.SUCCESS, list(self.resources)
            else:
                return MapperStatus.NO_MACHINE, []
        else:
            return MapperStatus.AUTHENTICATION_FAILED, []

    @property
    def name(self):
        return "SimpleMapper"

    @classmethod
    def create_from_dict(cls, data: Mapping[str, Any]):
        from interstate_love_song.settings import load_dict_into_dataclass

        settings = load_dict_into_dataclass(SimpleMapperSettings, data)
        return cls(settings.username, settings.password_hash, settings.resources)


if __name__ == "__main__":
    parser = argparse.ArgumentParser("hasher")
    parser.add_argument("PASSWORD")

    args = parser.parse_args()

    print(hash_pass(args.PASSWORD))