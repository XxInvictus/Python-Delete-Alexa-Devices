"""
Unit tests for models.py.

Covers: model instantiation, __repr__, and collection logic.
"""

from alexa_manager.models import (
    AlexaEntity,
    AlexaEntities,
    AlexaGroup,
    AlexaGroups,
    HAArea,
    AlexaExpandedGroup,
)
from unittest.mock import patch


class DummyEntity(AlexaEntity):
    def __init__(self):
        super().__init__(
            entity_id="dummy_id", display_name="Dummy", description="Dummy desc"
        )


def test_alexa_entity_repr():
    """
    Test __repr__ for AlexaEntity returns expected string.
    """
    entity = AlexaEntity("id1", "Lamp", "lamp via Home Assistant", "appl1")
    result = repr(entity)
    assert "AlexaEntity" in result
    assert "id1" in result
    assert "Lamp" in result
    assert "lamp via Home Assistant" in result
    assert "appl1" in result


def test_alexa_entities_add_and_repr():
    """
    Test adding AlexaEntity to AlexaEntities and __repr__.
    """
    entities = AlexaEntities()
    entity = AlexaEntity("id2", "Switch", "switch via Home Assistant")
    entities.add_entity(entity)
    assert entity in entities.entities
    assert "AlexaEntities" in repr(entities)


def test_ha_area_repr():
    """
    Test __repr__ for HAArea returns expected string.
    """
    area = HAArea("Living Room", ["light.lamp", "switch.tv"])
    result = repr(area)
    assert "Living Room" in result
    assert "light.lamp" in result
    assert "switch.tv" in result


def test_alexa_groups_add_and_repr():
    """
    Test adding AlexaGroup to AlexaGroups and __repr__.
    """
    groups = AlexaGroups()
    group = AlexaGroup("Bedroom", "group1")
    groups.add_group(group)
    assert group in groups.groups
    assert "AlexaGroups" in repr(groups)


def test_alexa_group_repr():
    """
    Test __repr__ for AlexaGroup returns expected string.
    """
    group = AlexaGroup("Kitchen", "group2")
    result = repr(group)
    assert "Kitchen" in result
    assert "group2" in result


def test_alexa_expanded_group_to_dict():
    """
    Test AlexaExpandedGroup to_dict returns expected dictionary.
    The defaults field may be a list of strings if sanitized by the model.
    """
    from alexa_manager.models import AlexaExpandedGroup

    group = AlexaExpandedGroup(
        name="Test Group",
        group_id="group123",
        entity_id="entity123",
        entity_type="GROUP",
        group_type="APPLIANCE",
        child_ids=["child1", "child2"],
        defaults=["{'type': 'default'}"],  # Model sanitizes dicts to strings
        associated_unit_ids=["unit1"],
        default_metadata_by_type={"type": "meta"},
        implicit_targeting_by_type={"type": "target"},
        appliance_ids=["appl1", "appl2"],
    )
    result = group.to_dict()
    assert result["name"] == "Test Group"
    assert result["id"] == "group123"
    assert result["entityId"] == "entity123"
    assert result["entityType"] == "GROUP"
    assert result["groupType"] == "APPLIANCE"
    assert result["childIds"] == ["child1", "child2"]
    # Accept stringified dicts for defaults, as per model sanitization
    assert result["defaults"] == ["{'type': 'default'}"]
    assert result["associatedUnitIds"] == ["unit1"]
    assert result["defaultMetadataByType"] == {"type": "meta"}
    assert result["implicitTargetingByType"] == {"type": "target"}
    assert result["applianceIds"] == ["appl1", "appl2"]


def test_alexa_expanded_group_repr():
    """
    Test __repr__ for AlexaExpandedGroup returns expected string.
    """
    group = AlexaExpandedGroup(name="Test Group", group_id="group123")
    result = repr(group)
    assert "AlexaGroup" in result
    assert "group123" in result
    assert "Test Group" in result


def test_get_request_dry_run():
    """
    Test that GET requests are executed and can be mocked in dry-run mode.
    Ensures unit tests remain DRY and do not make real network calls.
    """
    with patch("requests.get") as mock_get:
        mock_get.return_value.status_code = 404
        entity = DummyEntity()
        # _check_deleted should call requests.get and return True for 404
        result = entity._check_deleted()
        mock_get.assert_called_once()
        assert result is True
