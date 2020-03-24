import pytest
from interstate_love_song.plugins import *


def test_find_builtin_plugins():
    assert all(item in get_available_plugins().keys() for item in ["SimpleMapper"])


def test_no_configured_plugin():
    with pytest.raises(PluginError) as excinfo:
        create_plugin_from_settings({})
    assert str(excinfo.value) == "No plugin defined in mapper settings."


def test_unknown_plugin_type():
    with pytest.raises(PluginError) as excinfo:
        create_plugin_from_settings({"plugin": "Bogus"})
    assert str(excinfo.value) == 'Invalid plugin type: "Bogus"'


def test_simplemapper_missing_settings(caplog):
    with caplog.at_level(logging.ERROR):
        with pytest.raises(PluginError) as e:
            create_plugin_from_settings({"plugin": "SimpleMapper"})
        assert "Failed to configure plugin: SimpleMapper" in caplog.text
