"""
Unit tests for api.py.

Covers: API data fetching, error handling, and mapping logic.
"""

import pytest
from alexa_manager.api import get_entities, update_alexa_group
from alexa_manager.models import AlexaEntities


def test_get_entities_empty(monkeypatch):
    """
    Test get_entities returns empty AlexaEntities on empty response.
    """

    class MockEmptyResponse:
        text = ""

        def json(self):
            return []

    monkeypatch.setattr("requests.get", lambda *args, **kwargs: MockEmptyResponse())
    entities_result = get_entities()
    assert isinstance(entities_result, AlexaEntities)
    assert entities_result.entities == []


def test_get_entities_malformed_json(monkeypatch):
    """
    Test get_entities handles malformed JSON gracefully.
    """

    class MockMalformedResponse:
        text = "bad json"

        def json(self):
            raise ValueError("bad json")

    monkeypatch.setattr("requests.get", lambda *args, **kwargs: MockMalformedResponse())
    entities_result = get_entities()
    assert isinstance(entities_result, AlexaEntities)
    assert entities_result.entities == []


def test_update_alexa_group_success(monkeypatch):
    """
    Test update_alexa_group returns True on successful PUT.
    """
    # Example group data (simulates GET response)
    groups = [
        {
            "id": "group123",
            "entityId": "entity123",
            "name": "Test Group",
            "entityType": "GROUP",
            "groupType": "APPLIANCE",
            "childIds": ["child1", "child2"],
            "defaults": [],
            "associatedUnitIds": [],
            "defaultMetadataByType": {},
            "implicitTargetingByType": {},
            "applianceIds": [],
        }
    ]
    updated_fields = {"name": "Updated Group"}

    class FakeResponse:
        status_code = 200
        text = "OK"

    monkeypatch.setattr("requests.put", lambda *a, **k: FakeResponse())
    result = update_alexa_group("group123", updated_fields, groups)
    assert result is True


def test_update_alexa_group_not_found():
    """
    Test update_alexa_group raises ValueError if group not found.
    """
    groups = [{"id": "group123", "name": "Test Group"}]
    updated_fields = {"name": "Updated Group"}
    with pytest.raises(ValueError):
        update_alexa_group("missing_id", updated_fields, groups)


def test_update_alexa_group_failure(monkeypatch):
    """
    Test update_alexa_group returns False on failed PUT.
    """
    groups = [{"id": "group123", "name": "Test Group"}]
    updated_fields = {"name": "Updated Group"}

    class FakeResponse:
        status_code = 400
        text = "Bad Request"

    monkeypatch.setattr("requests.put", lambda *a, **k: FakeResponse())
    result = update_alexa_group("group123", updated_fields, groups)
    assert result is False


def test_update_alexa_group_exception(monkeypatch):
    """
    Test update_alexa_group returns False on request exception.
    """
    groups = [{"id": "group123", "name": "Test Group"}]
    updated_fields = {"name": "Updated Group"}

    def raise_exc(*a, **k):
        raise Exception("Network error")

    monkeypatch.setattr("requests.put", raise_exc)
    result = update_alexa_group("group123", updated_fields, groups)
    assert result is False


def test_find_group_by_id_found():
    """
    Test find_group_by_id returns the correct group when found.
    """
    from alexa_manager.api import find_group_by_id

    groups = [
        {"id": "group1", "name": "Group 1"},
        {"id": "group2", "name": "Group 2"},
    ]
    result = find_group_by_id(groups, "group2")
    assert result["name"] == "Group 2"


def test_find_group_by_id_not_found():
    """
    Test find_group_by_id raises ValueError when group is not found.
    """
    from alexa_manager.api import find_group_by_id

    groups = [{"id": "group1", "name": "Group 1"}]
    import pytest

    with pytest.raises(ValueError):
        find_group_by_id(groups, "missing")


def test_put_alexa_group_success(monkeypatch):
    """
    Test put_alexa_group returns True on successful PUT.
    """
    from alexa_manager.api import put_alexa_group

    group_data = {
        "id": "group123",
        "name": "Test Group",
        "entityId": "entity123",
        "entityType": "GROUP",
        "groupType": "APPLIANCE",
        "childIds": [],
        "defaults": [],
        "associatedUnitIds": [],
        "defaultMetadataByType": {},
        "implicitTargetingByType": {},
        "applianceIds": [],
    }
    updated_fields = {"name": "Updated Group"}

    class FakeResponse:
        status_code = 200
        text = "OK"

    monkeypatch.setattr("requests.put", lambda *a, **k: FakeResponse())
    result = put_alexa_group(group_data, updated_fields)
    assert result is True


def test_put_alexa_group_failure(monkeypatch):
    """
    Test put_alexa_group returns False on failed PUT.
    """
    from alexa_manager.api import put_alexa_group

    group_data = {"id": "group123", "name": "Test Group"}
    updated_fields = {"name": "Updated Group"}

    class FakeResponse:
        status_code = 400
        text = "Bad Request"

    monkeypatch.setattr("requests.put", lambda *a, **k: FakeResponse())
    result = put_alexa_group(group_data, updated_fields)
    assert result is False


def test_update_alexa_groups_batch(monkeypatch):
    """
    Test update_alexa_groups_batch processes multiple updates and returns correct results.
    """
    from alexa_manager.api import update_alexa_groups_batch

    # Patch update_alexa_group to simulate success/failure
    def fake_update_alexa_group(group_id, updated_fields, groups, url_base, headers):
        return group_id != "fail_id"

    monkeypatch.setattr("alexa_manager.api.update_alexa_group", fake_update_alexa_group)
    groups = [
        {"id": "group1", "name": "Group 1"},
        {"id": "fail_id", "name": "Group Fail"},
    ]
    updates = [
        {"group_id": "group1", "updated_fields": {"name": "New Name 1"}},
        {"group_id": "fail_id", "updated_fields": {"name": "Should Fail"}},
    ]
    results = update_alexa_groups_batch(updates, groups)
    assert results["group1"] is True
    assert results["fail_id"] is False


def test_update_alexa_groups_batch_empty(monkeypatch):
    """
    Test update_alexa_groups_batch with empty updates and groups lists.
    Should return an empty result dict.
    """
    from alexa_manager.api import update_alexa_groups_batch

    results = update_alexa_groups_batch([], [])
    assert results == {}


def test_update_alexa_groups_batch_invalid_type(monkeypatch):
    """
    Test update_alexa_groups_batch with invalid input types.
    Should raise TypeError or handle gracefully.
    """
    from alexa_manager.api import update_alexa_groups_batch

    try:
        update_alexa_groups_batch(None, None)
    except Exception as e:
        assert isinstance(e, TypeError)


def test_update_alexa_groups_batch_exception(monkeypatch):
    """
    Test update_alexa_groups_batch handles exceptions in update_alexa_group.
    Should log error and set result to False for failed group.
    """
    from alexa_manager.api import update_alexa_groups_batch

    def fake_update_alexa_group(group_id, updated_fields, groups, url_base, headers):
        if group_id == "error_id":
            raise ValueError("Simulated error")
        return True

    monkeypatch.setattr("alexa_manager.api.update_alexa_group", fake_update_alexa_group)
    groups = [{"id": "error_id", "name": "Error Group"}]
    updates = [{"group_id": "error_id", "updated_fields": {"name": "Should Error"}}]
    results = update_alexa_groups_batch(updates, groups)
    assert results["error_id"] is False


def test_update_alexa_groups_batch_large(monkeypatch):
    """
    Test update_alexa_groups_batch with a large number of updates.
    Should process all updates and return correct results.
    """
    from alexa_manager.api import update_alexa_groups_batch

    def fake_update_alexa_group(group_id, updated_fields, groups, url_base, headers):
        return True

    monkeypatch.setattr("alexa_manager.api.update_alexa_group", fake_update_alexa_group)
    groups = [{"id": f"group{i}", "name": f"Group {i}"} for i in range(100)]
    updates = [
        {"group_id": f"group{i}", "updated_fields": {"name": f"New Name {i}"}}
        for i in range(100)
    ]
    results = update_alexa_groups_batch(updates, groups)
    assert all(results.values())


def test_sync_ha_alexa_groups_create(monkeypatch):
    """
    Test sync_ha_alexa_groups creates missing Alexa groups with correct entities.
    """
    from alexa_manager.api import sync_ha_alexa_groups

    ha_areas = {"Living Room": ["light.lamp"]}
    alexa_groups = []
    ha_to_alexa = {"Living Room": ["appl1"]}

    class FakeResponse:
        status_code = 200
        text = "OK"

    monkeypatch.setattr("requests.post", lambda *a, **k: FakeResponse())
    result = sync_ha_alexa_groups(
        ha_areas, alexa_groups, ha_to_alexa, mode="update_only"
    )
    assert "Living Room" in result["created"]


def test_sync_ha_alexa_groups_update_only(monkeypatch):
    """
    Test sync_ha_alexa_groups adds missing entities in update_only mode.
    """
    from alexa_manager.api import sync_ha_alexa_groups

    ha_areas = {"Bedroom": ["switch.tv"]}
    alexa_groups = [{"name": "Bedroom", "id": "group1", "applianceIds": ["appl1"]}]
    ha_to_alexa = {"Bedroom": ["appl1", "appl2"]}
    monkeypatch.setattr("alexa_manager.api.update_alexa_group", lambda *a, **k: True)
    result = sync_ha_alexa_groups(
        ha_areas, alexa_groups, ha_to_alexa, mode="update_only"
    )
    assert "Bedroom" in result["updated"]


def test_sync_ha_alexa_groups_full(monkeypatch):
    """
    Test sync_ha_alexa_groups adds/removes entities in full mode.
    """
    from alexa_manager.api import sync_ha_alexa_groups

    ha_areas = {"Kitchen": ["sensor.temp"]}
    alexa_groups = [
        {"name": "Kitchen", "id": "group2", "applianceIds": ["appl1", "appl2"]}
    ]
    ha_to_alexa = {"Kitchen": ["appl3"]}
    monkeypatch.setattr("alexa_manager.api.update_alexa_group", lambda *a, **k: True)
    result = sync_ha_alexa_groups(ha_areas, alexa_groups, ha_to_alexa, mode="full")
    assert "Kitchen" in result["updated"]


def test_sync_ha_alexa_groups_skipped(monkeypatch):
    """
    Test sync_ha_alexa_groups skips groups that are already in sync.
    """
    from alexa_manager.api import sync_ha_alexa_groups

    ha_areas = {"Office": ["light.desk"]}
    alexa_groups = [{"name": "Office", "id": "group3", "applianceIds": ["appl4"]}]
    ha_to_alexa = {"Office": ["appl4"]}
    result = sync_ha_alexa_groups(ha_areas, alexa_groups, ha_to_alexa, mode="full")
    assert "Office" in result["skipped"]


def test_find_missing_ha_groups():
    """
    Test find_missing_ha_groups returns correct missing HA areas.
    """
    from alexa_manager.api import find_missing_ha_groups

    ha_areas = {"Living Room": [], "Bedroom": []}
    alexa_groups = [{"name": "Living Room"}]
    missing = find_missing_ha_groups(ha_areas, alexa_groups)
    assert missing == ["Bedroom"]


def test_create_alexa_group_for_ha_area(monkeypatch):
    """
    Test create_alexa_group_for_ha_area returns True on successful creation.
    """
    from alexa_manager.api import create_alexa_group_for_ha_area

    class FakeResponse:
        status_code = 200

    monkeypatch.setattr("requests.post", lambda *a, **k: FakeResponse())
    result = create_alexa_group_for_ha_area("Office", ["appl1"], "fake_url", {})
    assert result is True


def test_create_alexa_group_for_ha_area_failure(monkeypatch):
    """
    Test create_alexa_group_for_ha_area returns False on failed creation.
    """
    from alexa_manager.api import create_alexa_group_for_ha_area

    class FakeResponse:
        status_code = 400

    monkeypatch.setattr("requests.post", lambda *a, **k: FakeResponse())
    result = create_alexa_group_for_ha_area("Office", ["appl1"], "fake_url", {})
    assert result is False


def test_sync_alexa_group_entities_update_only(monkeypatch):
    """
    Test sync_alexa_group_entities adds missing entities in update_only mode.
    """
    from alexa_manager.api import sync_alexa_group_entities

    group = {"id": "group1", "applianceIds": ["appl1"]}
    desired_appliance_ids = ["appl1", "appl2"]
    monkeypatch.setattr("alexa_manager.api.update_alexa_group", lambda *a, **k: True)
    result = sync_alexa_group_entities(
        group, desired_appliance_ids, "update_only", [group], "fake_url", {}
    )
    assert result == "updated"


def test_sync_alexa_group_entities_full(monkeypatch):
    """
    Test sync_alexa_group_entities adds/removes entities in full mode.
    """
    from alexa_manager.api import sync_alexa_group_entities

    group = {"id": "group2", "applianceIds": ["appl1", "appl2"]}
    desired_appliance_ids = ["appl3"]
    monkeypatch.setattr("alexa_manager.api.update_alexa_group", lambda *a, **k: True)
    result = sync_alexa_group_entities(
        group, desired_appliance_ids, "full", [group], "fake_url", {}
    )
    assert result == "updated"


def test_sync_alexa_group_entities_skipped():
    """
    Test sync_alexa_group_entities skips when already in sync.
    """
    from alexa_manager.api import sync_alexa_group_entities

    group = {"id": "group3", "applianceIds": ["appl4"]}
    desired_appliance_ids = ["appl4"]
    result = sync_alexa_group_entities(
        group, desired_appliance_ids, "full", [group], "fake_url", {}
    )
    assert result == "skipped"


def test_get_entities_large_response(monkeypatch):
    """
    Test get_entities handles a large response efficiently and correctly.
    """

    class FakeResponse:
        def json(self):
            return [
                {
                    "id": str(i),
                    "displayName": f"Entity {i}",
                    "description": f"Description {i}",
                }
                for i in range(1000)
            ]

        text = "large json"

    monkeypatch.setattr("requests.get", lambda *a, **k: FakeResponse())
    entities = get_entities()
    assert len(entities.entities) == 1000


def test_update_alexa_group_invalid_data(monkeypatch):
    """
    Test update_alexa_group handles invalid group data (missing keys).
    """
    groups = [{"name": "Test Group"}]  # Missing 'id'
    updated_fields = {"name": "Updated Group"}
    with pytest.raises(ValueError):
        update_alexa_group("group123", updated_fields, groups)


def test_update_alexa_group_timeout(monkeypatch):
    """
    Test update_alexa_group handles request timeout gracefully.
    """
    groups = [{"id": "group123", "name": "Test Group"}]
    updated_fields = {"name": "Updated Group"}
    import requests

    def raise_timeout(*a, **k):
        raise requests.Timeout("Timeout error")

    monkeypatch.setattr("requests.put", raise_timeout)
    result = update_alexa_group("group123", updated_fields, groups)
    assert result is False


def test_find_group_by_id_duplicate_ids():
    """
    Test find_group_by_id returns the first match when duplicate IDs exist.
    """
    from alexa_manager.api import find_group_by_id

    groups = [
        {"id": "dup", "name": "First"},
        {"id": "dup", "name": "Second"},
    ]
    result = find_group_by_id(groups, "dup")
    assert result["name"] == "First"
