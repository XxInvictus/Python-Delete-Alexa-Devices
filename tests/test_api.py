"""
test_api.py

Unit tests for Alexa Media Player command functions in api.py.
"""

import pytest
from unittest.mock import patch, MagicMock
import requests
import tenacity
from alexa_manager import api


# Test: send_alexa_command_via_ha_service success
@patch("alexa_manager.api.requests.post")
def test_send_alexa_command_success(mock_post):
    """
    Test that send_alexa_command_via_ha_service returns device/entity ID on status 200.
    All network calls are mocked to prevent real HTTP requests.
    """
    mock_post.return_value.status_code = 200
    # Simulate device_id used
    with (
        patch("alexa_manager.api.ALEXA_DEVICE_ID", "device123"),
        patch("alexa_manager.api.ALEXA_ENTITY_ID", ""),
    ):
        result = api.send_alexa_command_via_ha_service("discover devices")
        assert result == "device123"
    # Simulate entity_id used
    with (
        patch("alexa_manager.api.ALEXA_DEVICE_ID", ""),
        patch("alexa_manager.api.ALEXA_ENTITY_ID", "entity456"),
    ):
        result = api.send_alexa_command_via_ha_service("discover devices")
        assert result == "entity456"


# Test: send_alexa_command_via_ha_service failure
@patch("alexa_manager.api.requests.post")
@patch("alexa_manager.api.fetch_last_used_alexa", return_value="media_player.test_echo")
def test_send_alexa_command_failure(mock_fetch_last_used, mock_post):
    """
    Test that send_alexa_command_via_ha_service raises RetryError on non-200 status.
    All network calls are mocked to prevent real HTTP requests.
    """
    mock_post.return_value.status_code = 500
    with pytest.raises(tenacity.RetryError) as exc_info:
        api.send_alexa_command_via_ha_service("discover devices")
    # Optionally check the cause is HTTPError
    assert isinstance(exc_info.value.last_attempt.exception(), requests.HTTPError)


# Test: send_alexa_command_via_ha_service missing config
@patch("alexa_manager.api.requests.post")
def test_send_alexa_command_missing_config(mock_post):
    """
    Test that send_alexa_command_via_ha_service raises ValueError if config is missing.
    All network calls are mocked to prevent real HTTP requests.
    """
    # Patch config values directly using monkeypatch pattern
    with (
        patch("alexa_manager.api.ALEXA_DEVICE_ID", ""),
        patch("alexa_manager.api.ALEXA_ENTITY_ID", ""),
        patch("alexa_manager.api.fetch_last_used_alexa", return_value=""),
    ):
        with pytest.raises(ValueError):
            api.send_alexa_command_via_ha_service("discover devices")


# Test: alexa_discover_devices delegates to send_alexa_command_via_ha_service
@patch("alexa_manager.api.requests.post")
@patch("alexa_manager.api.send_alexa_command_via_ha_service")
def test_alexa_discover_devices_delegation(mock_send, mock_post):
    """
    Test that alexa_discover_devices calls send_alexa_command_via_ha_service with correct command and returns the ID.
    All network calls are mocked to prevent real HTTP requests.
    """
    mock_send.return_value = "entity789"
    result = api.alexa_discover_devices()
    assert result == "entity789"
    mock_send.assert_called_once_with("discover devices")


@patch("alexa_manager.api.requests.post")
def test_get_ha_areas_success(mock_post):
    """
    Test get_ha_areas returns parsed area dict on valid response.
    """
    mock_post.return_value.status_code = 200
    mock_post.return_value.text = '{"Living Room":["light.lamp1","switch.tv"]}'
    result = api.get_ha_areas()
    assert result == {"Living Room": ["light.lamp1", "switch.tv"]}


@patch("alexa_manager.api.requests.post")
def test_get_ha_areas_invalid_json(mock_post):
    """
    Test get_ha_areas returns empty dict on invalid JSON response.
    """
    mock_post.return_value.status_code = 200
    mock_post.return_value.text = "not a json"
    result = api.get_ha_areas()
    assert result == {}


@patch("alexa_manager.api.requests.post")
def test_get_ha_areas_api_error(mock_post):
    """
    Test get_ha_areas returns empty dict on API error.
    """
    mock_post.return_value.status_code = 500
    mock_post.return_value.text = "Internal Server Error"
    result = api.get_ha_areas()
    assert result == {}


@patch("alexa_manager.api.requests.post")
def test_fetch_last_used_alexa_success(mock_post):
    """
    Test fetch_last_used_alexa returns entity_id string on valid response.
    """
    mock_post.return_value.status_code = 200
    mock_post.return_value.text = '"media_player.kitchen_echo"'
    result = api.fetch_last_used_alexa()
    assert result == "media_player.kitchen_echo"


@patch("alexa_manager.api.requests.post")
def test_fetch_last_used_alexa_empty(mock_post):
    """
    Test fetch_last_used_alexa returns empty string if no device found.
    """
    mock_post.return_value.status_code = 200
    mock_post.return_value.text = '""'
    result = api.fetch_last_used_alexa()
    assert result == ""


@patch("alexa_manager.api.requests.post")
def test_fetch_last_used_alexa_api_error(mock_post):
    """
    Test fetch_last_used_alexa returns empty string on API error.
    """
    mock_post.return_value.status_code = 500
    mock_post.return_value.text = "Internal Server Error"
    result = api.fetch_last_used_alexa()
    assert result == ""


@patch("alexa_manager.api.get_entities")
@patch("alexa_manager.api.alexa_discover_devices")
def test_wait_for_device_discovery_success(mock_discover, mock_get_entities):
    """
    Test wait_for_device_discovery returns True when new devices are discovered before timeout.
    """
    # Initial call returns 2 entities, then 2, then 3 (discovered)
    mock_get_entities.side_effect = [
        MagicMock(__len__=lambda s: 2),
        MagicMock(__len__=lambda s: 2),
        MagicMock(__len__=lambda s: 3),
    ]
    mock_discover.return_value = None
    result = api.wait_for_device_discovery(timeout=10, poll_interval=0.01)
    assert result is True


@patch("alexa_manager.api.get_entities")
@patch("alexa_manager.api.alexa_discover_devices")
def test_wait_for_device_discovery_timeout(mock_discover, mock_get_entities):
    """
    Test wait_for_device_discovery returns False if no new devices are discovered before timeout.
    """
    # Always returns 2 entities
    mock_get_entities.return_value = MagicMock(__len__=lambda s: 2)
    mock_discover.return_value = None
    result = api.wait_for_device_discovery(timeout=0.05, poll_interval=0.01)
    assert result is False


@patch("alexa_manager.api.get_entities", side_effect=Exception("fetch error"))
@patch("alexa_manager.api.alexa_discover_devices")
def test_wait_for_device_discovery_initial_fetch_error(
    mock_discover, mock_get_entities
):
    """
    Test wait_for_device_discovery returns False if initial entity fetch fails.
    """
    result = api.wait_for_device_discovery(timeout=1, poll_interval=0.01)
    assert result is False


@patch("alexa_manager.api.get_entities")
@patch(
    "alexa_manager.api.alexa_discover_devices", side_effect=Exception("discover error")
)
def test_wait_for_device_discovery_discover_error(mock_discover, mock_get_entities):
    """
    Test wait_for_device_discovery returns False if discovery trigger fails.
    """
    mock_get_entities.return_value = MagicMock(__len__=lambda s: 2)
    result = api.wait_for_device_discovery(timeout=1, poll_interval=0.01)
    assert result is False
