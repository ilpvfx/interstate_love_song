import base64
import json
import logging
from json import JSONDecodeError

import requests

from .base import *

from urllib.parse import urljoin

logger = logging.getLogger(__name__)


def _b64password(username: str, password: str):
    creds = username + ":" + password
    return base64.b64encode(creds.encode("utf-8")).decode("utf-8")


def _process_json(data) -> MapperResult:
    if "hosts" not in data:
        logger.error("hosts section missing from JSON in response.")
        return MapperStatus.INTERNAL_ERROR, []

    hosts = []
    try:
        hosts = list(data["hosts"])
    except TypeError:
        logger.error("hosts was not iterable.")
        return MapperStatus.INTERNAL_ERROR, []

    results = []
    for entry in hosts:
        if "name" not in entry:
            logger.error("name field missing from entry.")
            return MapperStatus.INTERNAL_ERROR, []
        if "hostname" not in entry:
            logger.error("hostname field missing from entry.")
            return MapperStatus.INTERNAL_ERROR, []

        results.append(Resource(str(entry["name"]), str(entry["hostname"])))

    return MapperStatus.SUCCESS, results


class SimpleWebserviceMapper(Mapper):
    """A mapper that uses a very simple remote webservice to authenticate and derive the mapping table.

    The SimpleWebserviceMapper was devised in a hurry during the latest pandemic. It calls another webservice and uses
    that as the mapper.

    It works with any endpoint that fulfills the following requirements:

    - The webservice must have an endpoint that either accepts the path "user=<username>" or the query param
        "user=<username>".

    - The webservice shall return UTF-8 JSON of the following format:

        {
          "hosts": [
                {
                    "name": "Bilbo Baggins",
                    "hostname": "jrr.tolkien.com",
                },
                {
                    "name": "Winston Smith",
                    "hostname": "orwell.mil",
                }
            ]
        }

    - The webservice shall accept HTTP Basic authentication.

    - If authentication fails, it should return Status 403.

    - If everything works, Status 200. "No resources" should be indicated with an empty hosts list.

    - Any other status codes (except redirects) are deemed as internal errors.

    Thus if the `base_url` is `http://oh.my.god.covid19.com`, then it will do `GET` requests to
    `http://oh.my.god.covid19.com/user=<username>`, with a `Authorization: Basic <b64>` header.
    """

    def __init__(self, base_url: str, use_query_parameter=False):
        """
        :param base_url: The path to the endpoint.
        :param use_query_parameter: Whether to use "/user=<username>" or "?user=<username>".
        """
        super().__init__()

        if base_url is None:
            raise ValueError("base_url cannot be None")
        self._base_url = str(base_url)

        if not isinstance(use_query_parameter, bool):
            raise ValueError("use_query_parameter must be a bool.")
        self._use_query_parameter = use_query_parameter
        if self._use_query_parameter:
            raise NotImplementedError()

    def map(self, credentials: Credentials, previous_host: Optional[str] = None) -> MapperResult:
        username, password = credentials
        username = str(username)
        password = str(password)

        headers = {"Authorization": "Basic {}".format(_b64password(username, password))}

        try:
            url = self._base_url + "/user={}".format(username)
            response = requests.get(url, headers=headers)

            if response.status_code == 403:
                return MapperStatus.AUTHENTICATION_FAILED, []
            elif response.status_code != 200:
                logger.error(
                    "The mapping webservice returned code %d, which is unsupported. The URL was %s",
                    response.status_code,
                    url,
                )
                return MapperStatus.INTERNAL_ERROR, []

            data = json.loads(
                response.text
            )  # use json instead of response.json() because it throws a weird exception.

            return _process_json(data)
        except requests.exceptions.ConnectionError:
            logger.error("Could not connect to the mapping webservice.")
            return MapperStatus.INTERNAL_ERROR, []
        except JSONDecodeError:
            logger.error("Could not decode JSON from the mapping webservice.")
            return MapperStatus.INTERNAL_ERROR, []

    @property
    def name(self):
        return "SimpleWebserviceMapper"
