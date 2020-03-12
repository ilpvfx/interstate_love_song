import base64
from dataclasses import dataclass

import pytest
import httpretty

from interstate_love_song.mapping.simplewebservice import (
    SimpleWebserviceMapper,
    MapperStatus,
    _b64password,
)


def test_simple_webservice_mapper_constructor_bad_arguments():
    with pytest.raises(ValueError):
        SimpleWebserviceMapper(None)
    with pytest.raises(ValueError):
        SimpleWebserviceMapper("http://blah.com", use_query_parameter="123")


TEST_BASE_URL = "http://orwell.mil"


@dataclass
class Fixture:
    mapper: SimpleWebserviceMapper


@pytest.fixture
def ctx() -> Fixture:
    return Fixture(SimpleWebserviceMapper(TEST_BASE_URL))


@httpretty.activate
def test_simple_webservice_mapper_webservice_receives_auth(ctx: Fixture):
    username = "Euler"
    password = "Leonhard"

    httpretty.register_uri(
        httpretty.GET,
        "{}/user={}".format(TEST_BASE_URL, username),
        body="Not found, my man!",
        status=404,
    )

    ctx.mapper.map((username, password))

    assert len(httpretty.latest_requests()) == 1
    assert "Authorization" in httpretty.latest_requests()[0].headers
    headers = httpretty.latest_requests()[0].headers

    assert headers["Authorization"] == "Basic {}".format(_b64password(username, password))


def test_simple_webservice_mapper_bad_credentials(ctx: Fixture):
    username = "Euler"
    password = "Leonhard"

    with pytest.raises(TypeError):
        ctx.mapper.map(123)


def test_simple_webservice_mapper_webservice_no_response(ctx: Fixture):
    username = "Euler"
    password = "Leonhard"

    status, resources = ctx.mapper.map((username, password))

    assert status == MapperStatus.INTERNAL_ERROR
    assert list(resources) == []


@httpretty.activate
def test_simple_webservice_mapper_webservice_returns_not_200(ctx: Fixture):
    username = "Euler"
    password = "Leonhard"

    httpretty.register_uri(
        httpretty.GET,
        "{}/user={}".format(TEST_BASE_URL, username),
        body="Not found, my man!",
        status=404,
    )

    status, resources = ctx.mapper.map((username, password))

    assert status == MapperStatus.INTERNAL_ERROR
    assert list(resources) == []


@httpretty.activate
def test_simple_webservice_mapper_webservice_returns_bad_json(ctx: Fixture):
    username = "Euler"
    password = "Leonhard"

    httpretty.register_uri(
        httpretty.GET, "{}/user={}".format(TEST_BASE_URL, username), body="{}}", status=200
    )

    status, resources = ctx.mapper.map((username, password))

    assert status == MapperStatus.INTERNAL_ERROR
    assert list(resources) == []


@httpretty.activate
def test_simple_webservice_mapper_webservice_returns_bad_json_missing_name(ctx: Fixture):
    username = "Euler"
    password = "Leonhard"

    machine_name1 = "A Machine"
    machine_hostname1 = "asimov.robotics.xyz"

    result_json = """{{
                "hosts": [
                    {{
                        "hostname": "{}"
                    }}
                ] 
            }}
            """.format(
        machine_name1, machine_hostname1
    )

    httpretty.register_uri(
        httpretty.GET, "{}/user={}".format(TEST_BASE_URL, username), body=result_json, status=200
    )

    status, resources = ctx.mapper.map((username, password))

    assert status == MapperStatus.INTERNAL_ERROR
    assert list(resources) == []


@httpretty.activate
def test_simple_webservice_mapper_webservice_returns_bad_json_missing_hostname(ctx: Fixture):
    username = "Euler"
    password = "Leonhard"

    machine_name1 = "A Machine"
    machine_hostname1 = "asimov.robotics.xyz"

    result_json = """{{
                "hosts": [
                    {{
                         "name": "{}"
                    }}
                ] 
            }}
            """.format(
        machine_name1, machine_hostname1
    )

    httpretty.register_uri(
        httpretty.GET, "{}/user={}".format(TEST_BASE_URL, username), body=result_json, status=200
    )

    status, resources = ctx.mapper.map((username, password))

    assert status == MapperStatus.INTERNAL_ERROR
    assert list(resources) == []


@httpretty.activate
def test_simple_webservice_mapper_webservice_returns_bad_json_hosts_not_iterable(ctx: Fixture):
    username = "Euler"
    password = "Leonhard"

    machine_name1 = "A Machine"
    machine_hostname1 = "asimov.robotics.xyz"

    result_json = """{{ "hosts": 123 }}""".format(machine_name1, machine_hostname1)

    httpretty.register_uri(
        httpretty.GET, "{}/user={}".format(TEST_BASE_URL, username), body=result_json, status=200
    )

    status, resources = ctx.mapper.map((username, password))

    assert status == MapperStatus.INTERNAL_ERROR
    assert list(resources) == []


@httpretty.activate
def test_simple_webservice_mapper_webservice_auth_fails(ctx: Fixture):
    username = "Euler"
    password = "Leonhard"

    httpretty.register_uri(
        httpretty.GET, "{}/user={}".format(TEST_BASE_URL, username), body="{}", status=403
    )

    status, resources = ctx.mapper.map((username, password))

    assert status == MapperStatus.AUTHENTICATION_FAILED
    assert list(resources) == []


@httpretty.activate
def test_simple_webservice_mapper_returns_resources(ctx: Fixture):
    username = "Euler"
    password = "Leonhard"

    machine_name1 = "A Machine"
    machine_hostname1 = "asimov.robotics.xyz"

    result_json = """{{
            "hosts": [
                {{
                    "name": "{}",
                    "hostname": "{}"
                }}
            ] 
        }}
        """.format(
        machine_name1, machine_hostname1
    )

    httpretty.register_uri(
        httpretty.GET, "{}/user={}".format(TEST_BASE_URL, username), body=result_json, status=200
    )

    status, resources = ctx.mapper.map((username, password))

    assert status == MapperStatus.SUCCESS
    resources = list(resources)

    assert len(resources) == 1
    assert resources[0].name == machine_name1
    assert resources[0].hostname == machine_hostname1
