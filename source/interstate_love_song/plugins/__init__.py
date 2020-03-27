import logging
import pkg_resources
import inspect
from typing import Mapping, Any
from ..mapping import Mapper

logger = logging.getLogger(__name__)


class PluginError(Exception):
    """Raised in response to errors reading Settings."""

    def __init__(self, msg):
        self._msg = msg

    def __str__(self):
        return self._msg

    @staticmethod
    def invalid_plugin_type(type_name):
        return PluginError('Invalid plugin type: "{}"'.format(type_name))


def get_builtin_plugin_modules():
    """Get builtin plugins from this module"""
    from . import simple

    return {
        "SIMPLE": simple,
    }


def get_discovered_plugin_modules():
    """Find modules that have defined their entrypoint as interstate_love_song.plugins"""
    return {
        entry_point.name: entry_point.load()
        for entry_point in pkg_resources.iter_entry_points(__name__)
    }


def get_available_plugins():
    """Get all available plugins from builtin and discovery"""
    plugin_modules = get_builtin_plugin_modules()
    plugin_modules.update(get_discovered_plugin_modules())
    plugins = {}
    for _, module in plugin_modules.items():
        members = inspect.getmembers(
            module,
            lambda member: inspect.isclass(member)
            and member is not Mapper
            and issubclass(member, Mapper),
        )
        logger.info(
            "Found plugins in module[%s]: %s",
            inspect.getmodulename(module.__file__),
            ", ".join(dict(members).keys()),
        )
        plugins.update(members)
    return plugins


def create_plugin_from_settings(settings: Mapping[str, Any]):
    from ..settings import SettingsError

    try:
        plugin_type_name = settings["plugin"]
    except KeyError:
        raise PluginError("No plugin defined in mapper settings.")

    plugins = get_available_plugins()
    plugin_type = None
    plugin_settings = {}

    try:
        plugin_type = plugins[plugin_type_name]
        plugin_settings = settings.get("settings")
        assert plugin_settings is not None
    except KeyError:
        raise PluginError.invalid_plugin_type(plugin_type_name)
    except AssertionError:
        logger.warning("No settings for plugin: %s, using defaults.", plugin_type_name)
        plugin_settings = {}

    try:
        return plugin_type.create_from_dict(plugin_settings)
    except SettingsError as e:
        logger.error("Failed to configure plugin: %s, %s", plugin_type_name, e)
    raise PluginError("Couldn't create plugin from settings: {}".format(settings))


if __name__ == "__main__":
    plugins = get_available_plugins()
    print(plugins)
