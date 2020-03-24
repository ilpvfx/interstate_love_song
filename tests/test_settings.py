import logging
import json
from typing import Mapping, Sequence, Any
from dataclasses import dataclass

from pytest import raises

from interstate_love_song import settings
import pytest
from argparse import Namespace

from interstate_love_song.mapping import Mapper, Resource

from interstate_love_song.plugins.simple import SimpleMapper


@dataclass
class DummyData:
    required: float
    a: str = "Riemann"
    b: int = 123


def test_load_dict_into_dataclass_defaults_set():
    data = settings.load_dict_into_dataclass(DummyData, {"required": 1.23})

    assert abs(data.required - 1.23) < 0.001
    assert data.a == "Riemann"
    assert data.b == 123


def test_load_dict_into_dataclass_raises_on_missing_property():
    with raises(settings.SettingsError):
        data = settings.load_dict_into_dataclass(DummyData, {})


def test_load_dict_into_dataclass_defaults_overridden():
    data = settings.load_dict_into_dataclass(DummyData, {"required": 1.23, "a": "Euler", "b": 321})

    assert abs(data.required - 1.23) < 0.001
    assert data.a == "Euler"
    assert data.b == 321


def test_load_dict_into_dataclass_converts_type():
    data = settings.load_dict_into_dataclass(DummyData, {"required": 1.23, "a": 123, "b": "321"})

    assert abs(data.required - 1.23) < 0.001
    assert data.a == "123"
    assert data.b == 321


def test_load_dict_into_dataclass_type_conversion_fails():
    with raises(settings.SettingsError):
        data = settings.load_dict_into_dataclass(
            DummyData, {"required": 1.23, "a": "Euler", "b": "hej"}
        )


@dataclass
class DummyData2:
    a: str = "Riemann"
    b: DummyData = DummyData(1.23)


def test_load_dict_into_dataclass_type_is_dataclass():
    data = settings.load_dict_into_dataclass(
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
    data = settings.load_dict_into_dataclass(
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
    data = settings.load_dict_into_dataclass(DummyData3, {"val": "A",})

    assert data.val == DummyEnum.A

    data = settings.load_dict_into_dataclass(DummyData3, {"val": "B",})

    assert data.val == DummyEnum.B

    with raises(settings.SettingsError):
        data = settings.load_dict_into_dataclass(DummyData3, {"val": "C",})


def test_load_settings_json():
    logging = Namespace(level="INFO")

    beaker = Namespace(type="Riemann", data_dir="Erdos",)

    simple_mapper = Namespace(
        plugin="SimpleMapper",
        username="Kurt",
        password_hash="Gödel",
        resource_name="Kurt's Machine",
        resource_hostname="kurt.godel.edu",
    )

    raw_settings_json = """
    {{
        "mapper": {{
            "plugin": "{mapper.plugin}",
            "settings": {{
                "username": "{mapper.username}", "password_hash": "{mapper.password_hash}",
                "resources": [{{
                    "name": "{mapper.resource_name}",
                    "hostname": "{mapper.resource_hostname}"
                }}]
            }}
        }},
        "logging": {{
            "level": "{logging.level}"
        }},
        "beaker": {{
            "type": "{beaker.type}",
            "data_dir": "{beaker.data_dir}"
        }}
    }}
    """.format(
        logging=logging, beaker=beaker, mapper=simple_mapper
    )

    result = settings.load_settings_json(raw_settings_json)

    assert isinstance(result.mapper, SimpleMapper)

    assert isinstance(result.logging, settings.LoggingSettings)
    assert result.logging.level == settings.LoggingLevel.INFO

    assert isinstance(result.beaker, settings.BeakerSettings)
    assert result.beaker.type == beaker.type
    assert result.beaker.data_dir == beaker.data_dir

    assert result.mapper.username == simple_mapper.username
    assert result.mapper.password_hash == simple_mapper.password_hash
    assert result.mapper.resources == [
        Resource(simple_mapper.resource_name, simple_mapper.resource_hostname)
    ]


def test_load_settings_json_missing_database():
    with pytest.raises(settings.SettingsError) as excinfo:
        raw_settings_json = "{}"
        settings.load_settings_json(raw_settings_json)
    assert str(excinfo.value) == "Property mapper was not set."
