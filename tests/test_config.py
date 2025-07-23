"""
Unit tests for config.py.

Covers: reading TOML, ensuring user config, merging configs, and error handling.
"""

import tomllib
import pytest
from alexa_manager.config import (
    load_config,
    read_toml_file,
    ensure_user_config_exists,
)


def test_read_toml_file_valid(tmp_path):
    """
    Test reading a valid TOML file returns the correct dictionary.
    """
    file = tmp_path / "test.toml"
    file.write_text('foo = "bar"\n')
    result = read_toml_file(str(file))
    assert result == {"foo": "bar"}


def test_read_toml_file_invalid(tmp_path):
    """
    Test reading an invalid TOML file raises TOMLDecodeError.
    """
    file = tmp_path / "bad.toml"
    file.write_text("bad toml")
    with pytest.raises(tomllib.TOMLDecodeError):
        read_toml_file(str(file))


def test_ensure_user_config_exists_toml(tmp_path):
    """
    Test that user config is created if it does not exist (TOML).
    """
    global_path = tmp_path / "global.toml"
    user_path = tmp_path / "user.toml"
    global_path.write_text("foo = 1\n")
    ensure_user_config_exists(str(global_path), str(user_path))
    assert user_path.exists()
    assert user_path.read_text() == "foo = 1\n"


def test_load_config_merges_toml(monkeypatch, tmp_path):
    """
    Test that load_config merges global and user TOML config, with user config taking precedence.
    """
    global_path = tmp_path / "global.toml"
    user_path = tmp_path / "user.toml"
    global_path.write_text("foo = 1\nbar = 2\n")
    user_path.write_text("bar = 3\nbaz = 4\n")
    monkeypatch.chdir(tmp_path)
    config = load_config(str(global_path), str(user_path))
    assert config["foo"] == 1
    assert config["bar"] == 3
    assert config["baz"] == 4
