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
