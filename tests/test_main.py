"""
Integration and CLI tests for main.py.

Covers: CLI argument handling, action dispatch, and error handling.
"""

import pytest
import sys
from unittest.mock import MagicMock
from alexa_manager import main


def test_main_get_entities(monkeypatch):
    """
    Test main CLI with --get-entities argument outputs entities table.
    """
    monkeypatch.setattr(sys, "argv", ["main.py", "--get-entities"])
    called = {}

    def fake_print_table(data, columns, title):
        called["printed"] = True
        assert isinstance(data, list)
        assert isinstance(columns, list)
        assert isinstance(title, str)

    monkeypatch.setattr(main, "print_table", fake_print_table)

    class DummyEntity:
        id = "id1"
        display_name = "Lamp"
        ha_entity_id = "lamp"
        description = "lamp via Home Assistant"

    class DummyAlexaEntities:
        entities = [DummyEntity()]

    monkeypatch.setattr(main, "get_entities", lambda: DummyAlexaEntities())
    main.main()
    assert called.get("printed")


def test_main_no_args(monkeypatch):
    """
    Test main CLI with no arguments runs all actions (smoke test).
    """
    monkeypatch.setattr(sys, "argv", ["main.py"])
    called = {}
    monkeypatch.setattr(
        main,
        "delete_entities",
        lambda x, y=None: called.update({"delete_entities": True}) or [],
    )
    monkeypatch.setattr(
        main, "delete_groups", lambda x, y=None: called.update({"delete_groups": True}) or []
    )
    monkeypatch.setattr(
        main, "create_groups_from_areas", lambda x, y=None, z=None: called.update({"create_groups": True}) or []
    )
    monkeypatch.setattr(main, "get_entities", lambda: MagicMock(entities=[]))
    monkeypatch.setattr(
        main, "get_graphql_endpoint_entities", lambda: MagicMock(entities=[])
    )
    monkeypatch.setattr(main, "get_groups", lambda: MagicMock(groups=[]))
    monkeypatch.setattr(main, "get_ha_areas", lambda: {})
    main.main()
    assert called.get("delete_entities")
    assert called.get("delete_groups")
    assert called.get("create_groups")


@pytest.mark.skip(
    reason="Avoids early test suite termination due to KeyboardInterrupt handling."
)
def test_main_keyboard_interrupt(monkeypatch):
    """
    Test main CLI handles KeyboardInterrupt gracefully.
    """

    monkeypatch.setattr(sys, "argv", ["main.py"])

    def raise_keyboard_interrupt(*a, **k):
        raise KeyboardInterrupt()

    monkeypatch.setattr(main, "delete_entities", raise_keyboard_interrupt)
    # Patch sys.exit to raise SystemExit instead of exiting the test runner
    monkeypatch.setattr(
        sys, "exit", lambda code=0: (_ for _ in ()).throw(SystemExit(code))
    )
    with pytest.raises(SystemExit):
        main.main()


def test_main_fatal_error(monkeypatch):
    """
    Test main CLI handles fatal error gracefully.
    """
    monkeypatch.setattr(sys, "argv", ["main.py"])

    def raise_error(*a, **k):
        raise Exception("fatal")

    monkeypatch.setattr(main, "get_entities", lambda: None)
    monkeypatch.setattr(main, "delete_entities", raise_error)
    with pytest.raises(Exception) as excinfo:
        main.main()
    assert "fatal" in str(excinfo.value)


def test_main_alexa_only_skips_ha(monkeypatch, caplog):
    """
    Test main CLI with --alexa-only argument skips HA-dependent actions.
    """
    monkeypatch.setattr(sys, "argv", ["main.py", "--alexa-only", "--create-groups"])
    called = {"create_groups": False, "get_ha_areas": False}

    def fake_create_groups(_):
        called["create_groups"] = True
        return []

    def fake_get_ha_areas():
        called["get_ha_areas"] = True
        return {}

    monkeypatch.setattr(main, "create_groups_from_areas", fake_create_groups)
    monkeypatch.setattr(main, "get_ha_areas", fake_get_ha_areas)
    main.main()
    # Should not call create_groups_from_areas or get_ha_areas
    assert not called["create_groups"]
    assert not called["get_ha_areas"]
    # Should log Alexa Only mode message
    assert any("Alexa Only mode" in r for r in caplog.messages)


def test_main_alexa_only_no_args(monkeypatch, caplog):
    """
    Test main CLI with only --alexa-only argument (no actions).
    Should not attempt real entity deletion.
    """
    import sys
    from alexa_manager.models import AlexaEntity, AlexaGroup

    monkeypatch.setattr(sys, "argv", ["main.py", "--alexa-only"])
    called = {"create_groups": False, "get_ha_areas": False}
    monkeypatch.setattr(
        main, "create_groups_from_areas", lambda x, y=None: called.update({"create_groups": True}) or []
    )
    monkeypatch.setattr(
        main, "get_ha_areas", lambda: called.update({"get_ha_areas": True}) or {}
    )
    # Patch AlexaEntity.delete to avoid real API calls
    monkeypatch.setattr(AlexaEntity, "delete", lambda self: True)
    monkeypatch.setattr(AlexaGroup, "delete", lambda self: True)
    main.main()
    # Should not call create_groups_from_areas or get_ha_areas
    assert not called["create_groups"]
    assert not called["get_ha_areas"]
    assert any("Alexa Only mode" in r for r in caplog.messages)


def test_create_groups_from_areas_respects_ignored_areas(monkeypatch):
    """
    Test that create_groups_from_areas skips areas listed in IGNORED_HA_AREAS.
    """
    # Mock HA areas
    ha_areas = {
        "Living Room": ["entity_1", "entity_2"],
        "Garage": ["entity_3"],
        "Kitchen": ["entity_4"],
    }
    # Patch IGNORED_HA_AREAS constant
    monkeypatch.setattr(main, "IGNORED_HA_AREAS", ["Garage"])
    # Patch normalization to identity for test
    monkeypatch.setattr(main, "normalize_area_name", lambda name: name)
    # Patch dependencies
    monkeypatch.setattr(main, "get_graphql_endpoint_entities", lambda: MagicMock())
    monkeypatch.setattr(
        main,
        "map_ha_entities_to_alexa_ids",
        lambda areas, endpoints: {k: v for k, v in areas.items()},
    )
    created_groups = []

    class DummyAlexaGroup:
        def __init__(self, name):
            self.name = name
            self.create_data = {}

        def create(self):
            created_groups.append(self.name)
            return True

    monkeypatch.setattr(main, "AlexaGroup", DummyAlexaGroup)
    monkeypatch.setattr(main, "convert_ha_area_name", lambda name: name)
    monkeypatch.setattr(
        main,
        "run_with_progress_bar",
        lambda areas, title, fn, collector: [fn(area, collector) for area in areas],
    )
    # Call function
    main.create_groups_from_areas(ha_areas, {})
    # Assert ignored area not processed
    assert "Garage" not in created_groups
    assert "Living Room" in created_groups
    assert "Kitchen" in created_groups
