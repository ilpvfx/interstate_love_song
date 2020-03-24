import inspect
import logging
import dataclasses
from dataclasses import dataclass, field
from typing import Mapping, Any, Union, TypeVar, Type, Optional, Sequence
from enum import Enum

import json
import argparse

from .mapping.base import Mapper
from .plugins import create_plugin_from_settings
from .plugins.simple import SimpleMapper, SimpleMapperSettings

logger = logging.getLogger(__name__)


class SettingsError(Exception):
    """Raised in response to errors reading Settings."""

    def __init__(self, msg):
        self._msg = msg

    def __str__(self):
        return self._msg

    @staticmethod
    def missing_property(name: str):
        return SettingsError("Property {} was not set.".format(name))


T = TypeVar("T")


def load_dict_into_dataclass(dc: Type[T], dict: Mapping[str, Any]) -> T:
    """Loads the fields from a dataclass, supports the following features:
        - name
        - default
        - type
    Assumes the dataclass has a default __init__.
    For each field in the dataclass, looks for a corresponding field in dict.

    If a field has a default it is allowed to be omitted from the dict. The final value is then the
    default.

    If a property name match exists, but the type mismatches, the type constructor is called on the value stored in the
    dict. If an exception is thrown, this will result in a SettingsError

    If a field is of a type that is a dataclass itself, that property should itself be represented by a dictionary.
    It will get loaded with a subsequent call to __load_dict_into_dataclass.

    If a field is of a type Sequence[T], it will expect a list of convertible values.

    It does not handle fields with a type that is a Union, like Optional[Something] or Union[str, int].

    :raises SettingsError: a field without a default was missing from the dict. A type conversion failed.
    """
    props = {}

    fields = dataclasses.fields(dc)

    def process(tp, val):
        if dataclasses.is_dataclass(tp):
            val = load_dict_into_dataclass(tp, val)
        elif hasattr(tp, "_name") and tp._name == "Sequence":
            val = [process(tp.__args__[0], item) for item in val]
        elif issubclass(tp, Enum):
            try:
                val = tp[str(val)]
            except KeyError as ke:
                raise SettingsError("Failure to convert {} to enum of {}.".format(val, tp))
        elif type(val) != tp:
            try:
                val = tp(val)
            except Exception as e:
                raise SettingsError("Failure to convert value: {}".format(e))
        return val

    for f in fields:
        if f.init is False:
            continue
        if f.name in dict:
            val = dict[f.name]
            val = process(f.type, val)
            props[f.name] = val
        else:
            if f.default is dataclasses.MISSING:
                raise SettingsError("Field {} is required (has no default).".format(f.name))
            else:
                props[f.name] = f.default

    return dc(**props)


def _get_property(map: Mapping[str, str], name: str) -> Any:
    try:
        return map[name]
    except KeyError:
        raise SettingsError.missing_property(name)


@dataclass
class BeakerSettings:
    """Settings for the beaker session manager. See the beaker docs for more info."""

    type: str = "file"
    data_dir: str = "/tmp"


class LoggingLevel(Enum):
    INFO = "INFO"
    DEBUG = "DEBUG"


@dataclass
class LoggingSettings:
    level: LoggingLevel = LoggingLevel.INFO


@dataclass
class DefaultMapper:
    plugin: Type[SimpleMapper] = SimpleMapper
    settings: SimpleMapperSettings = SimpleMapperSettings()

    @classmethod
    def create_mapper(cls):
        return cls.plugin.create_from_dict(dataclasses.asdict(cls.settings))


@dataclass()
class Settings:
    """Holds the settings. Fields with a default may be omitted in the config."""

    mapper: Union[Type[Mapper], DefaultMapper] = field(init=False, default=DefaultMapper)
    logging: LoggingSettings = LoggingSettings()
    beaker: BeakerSettings = BeakerSettings()

    @classmethod
    def load_dict(cls, data: Mapping[str, Any]):
        """See load_settings_json for the expected structure."""
        return load_dict_into_dataclass(Settings, data)

    def json(self):
        pass


def load_settings_json(json_str: str) -> Settings:
    """Loads the settings from a JSON string. The JSON should be structured as follows:
        {
            "mapper": ?,
            "beaker": {"type": ?, "data_dir": ?},
            "logging": {"level": ?},
        }
    """
    data = json.loads(json_str)
    mapper = data.pop("mapper", None)
    settings = Settings.load_dict(data)
    if mapper is None:
        raise SettingsError.missing_property("mapper")
    settings.mapper = create_plugin_from_settings(mapper)
    return settings


def generate_default_json(dc: Type[T]) -> Mapping[str, Any]:
    fields = dataclasses.fields(dc)

    props = {}
    for f in fields:
        val = None
        if dataclasses.is_dataclass(f.type):
            val = generate_default_json(f.type)
        elif f.default is not dataclasses.MISSING:
            if dataclasses.is_dataclass(f.default):
                val = generate_default_json(f.default)
            elif isinstance(f.default, Enum):
                val = f.default.name
            elif inspect.isclass(f.default) and issubclass(f.default, Mapper):
                val = f.default.__name__
            else:
                val = f.default
        else:
            val = "REQUIRED {}".format(f.type)
        props[f.name] = val

    return props


if __name__ == "__main__":
    from .plugins.simple import SimpleMapper, SimpleMapperSettings

    defaults = generate_default_json(Settings)
    print(json.dumps(defaults, indent=2))
