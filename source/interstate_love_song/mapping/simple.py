import argparse

from .base import *
from hashlib import pbkdf2_hmac


def hash_pass(s: str, salt="IGNORED"):
    """Hash a password.

    Not the best way to store a password since the salt is known, but it offers a bit more protection than storing it
    plaintext."""
    return pbkdf2_hmac("sha256", s.encode("utf-8"), salt.encode("utf-8"), 100000).hex()


class SimpleMapper(Mapper):
    """A very simple mapper that accepts one set of credentials and returns a given set of hosts."""

    def __init__(self, username: str, password_hash: str, hosts: Sequence[str]):
        """

        :param username:
            The username to accept.
        :param password_hash:
            A password hash, output from hash_pass.
        :param hosts:
        :raises TypeError:
        """
        super().__init__()
        self._username = str(username)
        self._password_hash = str(password_hash)
        self._hosts = list(str(host) for host in hosts)

    @property
    def username(self) -> str:
        return self._username

    @property
    def password_hash(self) -> str:
        return self._password_hash

    @property
    def hosts(self) -> Sequence[str]:
        return self._hosts

    def map(self, credentials: Credentials, previous_host: Optional[str] = None) -> MapperResult:
        usr, psw = credentials
        if not isinstance(usr, str) or not isinstance(psw, str):
            raise ValueError("username and password must be strings.")

        if usr == self.username and hash_pass(psw) == self._password_hash:
            if self._hosts:
                return MapperStatus.SUCCESS, [Resource(host, host) for host in self.hosts]
            else:
                return MapperStatus.NO_MACHINE, []
        else:
            return MapperStatus.AUTHENTICATION_FAILED, []


if __name__ == "__main__":
    parser = argparse.ArgumentParser("hasher")
    parser.add_argument("PASSWORD")

    args = parser.parse_args()

    print(hash_pass(args.PASSWORD))
