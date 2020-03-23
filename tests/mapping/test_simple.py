from interstate_love_song.plugins.simple import SimpleMapper

import pytest

from interstate_love_song.plugins.simple import hash_pass, MapperStatus, Resource


def test_simple_mapper_constructor_bad_arguments():
    with pytest.raises(TypeError):
        SimpleMapper("Abcdef", "Euler", 123)


def test_simple_mapper_constructor():
    mapper = SimpleMapper(123, 123, [Resource("kolmogorov", "kolmogorov.ru")])
    assert mapper.username == "123"
    assert mapper.password_hash == "123"
    assert list(mapper.resources) == [Resource("kolmogorov", "kolmogorov.ru")]


def test_simple_mapper_constructor_accepts_no_resources():
    mapper = SimpleMapper("Euler", "Leonhard", [])
    assert list(mapper.resources) == []


def test_simple_mapper_map_bad_arguments():
    mapper = SimpleMapper("Euler", "Leonhard", [])
    with pytest.raises(ValueError):
        mapper.map((123, "Leonhard"))
    with pytest.raises(ValueError):
        mapper.map(("Euler", 123))


def test_simple_mapper_map_no_resources():
    mapper = SimpleMapper("Euler", hash_pass("Leonhard"), [])
    status, resources = mapper.map(("Euler", "Leonhard"))

    assert status == MapperStatus.NO_MACHINE
    assert list(resources) == []


def test_simple_mapper_map_bad_credentials():
    mapper = SimpleMapper("Euler", hash_pass("Leonhard"), [])
    status, hosts = mapper.map(("Euler", "wrong"))

    assert status == MapperStatus.AUTHENTICATION_FAILED
    assert list(hosts) == []


def test_simple_mapper_map():
    expected_hosts = [Resource(host, host) for host in ("abc.gov", "123.edu")]
    mapper = SimpleMapper("Euler", hash_pass("Leonhard"), expected_hosts)
    status, hosts = mapper.map(("Euler", "Leonhard"))

    assert status == MapperStatus.SUCCESS
    assert list(hosts) == expected_hosts
