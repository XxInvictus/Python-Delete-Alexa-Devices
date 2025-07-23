"""
Unit tests for api.py.

Covers: API data fetching, error handling, and mapping logic.
"""

from alexa_manager.api import get_entities
from alexa_manager.models import AlexaEntities


def test_get_entities_empty(monkeypatch):
    """
    Test get_entities returns empty AlexaEntities on empty response.
    """

    class FakeResponse:
        text = ""

        def json(self):
            return []

    monkeypatch.setattr("requests.get", lambda *a, **k: FakeResponse())
    entities = get_entities()
    assert isinstance(entities, AlexaEntities)
    assert entities.entities == []


def test_get_entities_malformed_json(monkeypatch):
    """
    Test get_entities handles malformed JSON gracefully.
    """

    class FakeResponse:
        text = "bad json"

        def json(self):
            raise ValueError("bad json")

    monkeypatch.setattr("requests.get", lambda *a, **k: FakeResponse())
    entities = get_entities()
    assert isinstance(entities, AlexaEntities)
    assert entities.entities == []
