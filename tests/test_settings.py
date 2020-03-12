import json
from typing import Sequence
from dataclasses import dataclass

from pytest import raises

from interstate_love_song import settings
import pytest
from argparse import Namespace

from interstate_love_song.mapping import Resource
from interstate_love_song.settings import MapperToUse


@dataclass
class DummyData:
    required: float
    a: str = "Riemann"
    b: int = 123


def test_load_dict_into_dataclass_defaults_set():
    data = settings._load_dict_into_dataclass(DummyData, {"required": 1.23})

    assert abs(data.required - 1.23) < 0.001
    assert data.a == "Riemann"
    assert data.b == 123


def test_load_dict_into_dataclass_raises_on_missing_property():
    with raises(settings.SettingsError):
        data = settings._load_dict_into_dataclass(DummyData, {})


def test_load_dict_into_dataclass_defaults_overridden():
    data = settings._load_dict_into_dataclass(DummyData, {"required": 1.23, "a": "Euler", "b": 321})

    assert abs(data.required - 1.23) < 0.001
    assert data.a == "Euler"
    assert data.b == 321


def test_load_dict_into_dataclass_converts_type():
    data = settings._load_dict_into_dataclass(DummyData, {"required": 1.23, "a": 123, "b": "321"})

    assert abs(data.required - 1.23) < 0.001
    assert data.a == "123"
    assert data.b == 321


def test_load_dict_into_dataclass_type_conversion_fails():
    with raises(settings.SettingsError):
        data = settings._load_dict_into_dataclass(
            DummyData, {"required": 1.23, "a": "Euler", "b": "hej"}
        )


@dataclass
class DummyData2:
    a: str = "Riemann"
    b: DummyData = DummyData(1.23)


def test_load_dict_into_dataclass_type_is_dataclass():
    data = settings._load_dict_into_dataclass(
        DummyData2, {"a": "Euler", "b": {"required": 1.23, "a": 123, "b": "321"}}
    )

    assert data.a == "Euler"
    assert isinstance(data.b, DummyData)
    assert abs(data.b.required - 1.23) < 0.001
    assert data.b.a == "123"
    assert data.b.b == 321


@dataclass
class DummyData4:
    a: Sequence[str]
    b: Sequence[DummyData]


def test_load_dict_into_dataclass_type_is_list():
    data = settings._load_dict_into_dataclass(
        DummyData4,
        {
            "a": ["Euler", "Leonhard"],
            "b": [{"required": 123, "a": "Test"}, {"required": 256, "b": 666}],
        },
    )

    assert data.a == ["Euler", "Leonhard"]
    assert isinstance(data.b, list)
    assert len(data.b) == 2

    assert data.b[0].required == 123.0
    assert data.b[0].a == "Test"
    assert data.b[0].b == 123

    assert data.b[1].required == 256.0
    assert data.b[1].a == "Riemann"
    assert data.b[1].b == 666


from enum import Enum


class DummyEnum(Enum):
    A = 1
    B = 2


@dataclass
class DummyData3:
    val: DummyEnum = DummyEnum.B


def test_load_dict_into_dataclass_enum_converted():
    data = settings._load_dict_into_dataclass(DummyData3, {"val": "A",})

    assert data.val == DummyEnum.A

    data = settings._load_dict_into_dataclass(DummyData3, {"val": "B",})

    assert data.val == DummyEnum.B

    with raises(settings.SettingsError):
        data = settings._load_dict_into_dataclass(DummyData3, {"val": "C",})


def test_load_settings_json():
    logging = Namespace(level="INFO")

    beaker = Namespace(type="Riemann", data_dir="Erdos",)

    simple_mapper = Namespace(
        username="Kurt",
        password_hash="Gödel",
        resource_name="Kurt's Machine",
        resource_hostname="kurt.godel.edu",
    )

    simple_webservice_mapper = Namespace(base_url="Kurt",)

    raw_settings_json = """
    {{
        "mapper": "SIMPLE",
        "logging": {{
            "level": "{logging.level}"
        }},
        "beaker": {{
            "type": "{beaker.type}",
            "data_dir": "{beaker.data_dir}"
        }},
        "simple_mapper" : {{
            "username": "{simple_mapper.username}", "password_hash": "{simple_mapper.password_hash}", 
            "resources": [{{
                "name": "{simple_mapper.resource_name}",
                "hostname": "{simple_mapper.resource_hostname}"
            }}]
        }},
        "simple_webservice_mapper": {{"base_url": "{simple_webservice_mapper.base_url}"}}

    }}
    """.format(
        logging=logging,
        beaker=beaker,
        simple_mapper=simple_mapper,
        simple_webservice_mapper=simple_webservice_mapper,
    )

    result = settings.load_settings_json(raw_settings_json)

    assert result.mapper == MapperToUse.SIMPLE

    assert isinstance(result.logging, settings.LoggingSettings)
    assert result.logging.level == settings.LoggingLevel.INFO

    assert isinstance(result.beaker, settings.BeakerSettings)
    assert result.beaker.type == beaker.type
    assert result.beaker.data_dir == beaker.data_dir

    assert isinstance(result.simple_mapper, settings.SimpleMapperSettings)
    assert result.simple_mapper.username == simple_mapper.username
    assert result.simple_mapper.password_hash == simple_mapper.password_hash
    assert result.simple_mapper.resources == [
        Resource(simple_mapper.resource_name, simple_mapper.resource_hostname)
    ]

    assert isinstance(result.simple_webservice_mapper, settings.SimpleWebserviceMapperSettings)
    assert result.simple_webservice_mapper.base_url == simple_webservice_mapper.base_url


def test_load_settings_json_missing_database():
    raw_settings_json = "{}"
    result = settings.load_settings_json(raw_settings_json)
