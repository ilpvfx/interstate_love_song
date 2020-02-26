import json
from dataclasses import dataclass

from pytest import raises

from interstate_love_song import settings
import pytest
from argparse import Namespace


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

    raw_settings_json = """
    {{
        "logging": {{
            "level": "{logging.level}",
        }},
        "beaker": {{
            "type": "{beaker.type}",
            "data_dir": "{beaker.data_dir}"
        }}
    }}
    """.format(
        logging=logging, beaker=beaker
    )

    result = settings.load_settings_json(raw_settings_json)

    assert isinstance(result.logging, settings.LoggingSettings)
    assert result.logging.level == settings.LoggingLevel.INFO

    assert isinstance(result.beaker, settings.BeakerSettings)
    assert result.beaker.type is beaker.type
    assert result.beaker.data_dir is beaker.data_dir


def test_load_settings_json_missing_database():
    raw_settings_json = "{}"
    result = settings.load_settings_json(raw_settings_json)
