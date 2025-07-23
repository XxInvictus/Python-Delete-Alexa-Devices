"""
models.py

Model classes for Alexa and Home Assistant entities and groups.

This module contains data models used throughout the Alexa management script.
"""

from typing import Any, Dict, List
from alexa_manager.config import (
    config,
    DEBUG,
    DO_NOT_DELETE,
    URLS,
    ALEXA_HEADERS,
)
import requests
from tenacity import (
    retry,
    retry_if_exception_type,
    stop_after_attempt,
    wait_exponential,
)
import logging

logger = logging.getLogger(__name__)


class AlexaEntities:
    """
    Represents a collection of Alexa entities.

    Attributes:
        entities (List[AlexaEntity]): List of AlexaEntity instances.
        filter_text (str): Text used to filter entities by description.
    """

    def __init__(self) -> None:
        self.entities: List[AlexaEntity] = []
        self.filter_text: str = config["DESCRIPTION_FILTER_TEXT"]

    def add_entity(self, entity: "AlexaEntity") -> None:
        """
        Add an AlexaEntity to the collection.

        Args:
            entity (AlexaEntity): The entity to add.
        """
        self.entities.append(entity)

    def __repr__(self) -> str:
        """
        Return a string representation of the AlexaEntities object.

        Returns:
            str: String representation of the object.
        """
        return f"AlexaEntities(entities={self.entities})"


class AlexaEntity:
    """
    Represents an Alexa entity (device or endpoint).

    Attributes:
        id (str): Unique identifier for the entity (applianceKey).
        display_name (str): Display name of the entity.
        description (str): Description of the entity.
        ha_entity_id (str): Normalized Home Assistant entity ID.
        delete_id (str): Identifier used for deletion.
        appliance_id (str): Alexa applianceId (from endpoints).
    """

    def __init__(
        self,
        entity_id: str,
        display_name: str,
        description: str,
        appliance_id: str = "",
    ) -> None:
        """
        Initialize an AlexaEntity object.

        Args:
            entity_id (str): The entity's unique identifier.
            display_name (str): The display name of the entity.
            description (str): Description of the entity.
            appliance_id (str): The Alexa applianceId (optional).
        """
        self.id: str = entity_id
        self.display_name: str = display_name
        self.description: str = description
        self.ha_entity_id: str = self.description.replace(
            " via Home Assistant", ""
        ).lower()
        self.delete_id: str = (
            self.description.replace(".", "%23")
            .replace(" via Home Assistant", "")
            .lower()
        )
        self.appliance_id: str = appliance_id

    def __repr__(self) -> str:
        """
        Return a string representation of the AlexaEntity object.

        Returns:
            str: String representation of the object.
        """
        return f"AlexaEntity(id={self.id}, displayName={self.display_name}, description={self.description}, appliance_id={self.appliance_id})"

    @retry(
        stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=1, max=10)
    )
    def delete(self) -> bool:
        """
        Delete the Alexa entity using the API.

        Returns:
            bool: True if deletion was successful, False otherwise.

        Raises:
            requests.HTTPError: If deletion fails after retries.
        """
        url = f"{URLS['DELETE_ENTITIES']}{self.delete_id}"
        if DO_NOT_DELETE:
            logger.info(f"Skipping deletion of entity {self.id} ({self.display_name})")
            return True
        response = requests.delete(url, headers=ALEXA_HEADERS, timeout=10)
        if DEBUG:
            logger.debug(f"Delete response status code: {response.status_code}")
            logger.debug(f"Delete response text: {response.text}")
        response.raise_for_status()
        if response.status_code == 204:
            return self._check_deleted()
        else:
            raise requests.HTTPError(
                f"Entity {self.id} deletion failed. Status code: {response.status_code}, Response: {response.text}"
            )

    @retry(
        retry=retry_if_exception_type(requests.exceptions.HTTPError),
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=1, max=10),
    )
    def _check_deleted(self) -> bool:
        """
        Check if the entity was deleted by querying the API.

        Returns:
            bool: True if entity is deleted (404), False otherwise.

        Raises:
            requests.HTTPError: If entity is not deleted.
        """
        url = f"https://{config['ALEXA_HOST']}/api/smarthome/v1/presentation/devices/control/{self.id}"
        response = requests.get(url, headers=ALEXA_HEADERS, timeout=10)
        if DEBUG:
            logger.debug(f"Check delete response status code: {response.status_code}")
            logger.debug(f"Check delete response text: {response.text}")
        if response.status_code != 404:
            raise requests.HTTPError(
                f"Entity {self.id} was not deleted. Status code: {response.status_code}, Response: {response.text}"
            )
        return response.status_code == 404


class HAArea:
    """
    Represents a Home Assistant area and its child entity IDs.

    Attributes:
        name (str): The name of the area.
        entity_ids (List[str]): List of child entity IDs in the area.
    """

    def __init__(self, name: str, entity_ids: List[str]):
        """
        Initialize a HAArea object.

        Args:
            name (str): The name of the area.
            entity_ids (List[str]): List of child entity IDs in the area.
        """
        self.name = name
        self.entity_ids = entity_ids

    def __repr__(self) -> str:
        """
        Return a string representation of the HAArea object.

        Returns:
            str: String representation of the object.
        """
        return f"HAArea(name={self.name}, entity_ids={self.entity_ids})"


class AlexaGroups:
    """
    Represents a collection of Alexa groups.

    Attributes:
        groups (List[AlexaGroup]): List of AlexaGroup instances.
    """

    def __init__(self):
        self.groups: List[AlexaGroup] = []

    def add_group(self, group: "AlexaGroup") -> None:
        """
        Add an AlexaGroup to the collection.

        Args:
            group (AlexaGroup): The group to add.
        """
        self.groups.append(group)

    def __repr__(self) -> str:
        """
        Return a string representation of the AlexaGroups object.

        Returns:
            str: String representation of the object.
        """
        return f"AlexaGroups(groups={self.groups})"


class AlexaGroup:
    """
    Represents an Alexa group.

    Attributes:
        id (str): Unique identifier for the group.
        name (str): Name of the group.
        create_data (Dict[str, Any]): Data used to create the group via API.
    """

    def __init__(self, name: str, group_id: str = "") -> None:
        """
        Initialize an AlexaGroup object.

        Args:
            name (str): The name of the group.
            group_id (str): The group's unique identifier (optional).
        """
        self.id: str = group_id
        self.name: str = name
        self.create_data: Dict[str, Any] = {
            "entityId": "",
            "id": "",
            "name": self.name,
            "entityType": "GROUP",
            "groupType": "APPLIANCE",
            "childIds": [],
            "defaults": [],
            "associatedUnitIds": [],
            "applianceIds": [],
        }

    def __repr__(self) -> str:
        """
        Return a string representation of the AlexaGroup object.

        Returns:
            str: String representation of the object.
        """
        return f"AlexaGroup(id={self.id}, name={self.name})"

    @retry(
        stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=1, max=10)
    )
    def create(self) -> bool:
        """
        Create the Alexa group using the API.

        Returns:
            bool: True if creation was successful, False otherwise.

        Raises:
            requests.HTTPError: If creation fails after retries.
        """
        url = URLS["CREATE_GROUP"]
        response = requests.post(
            url, headers=ALEXA_HEADERS, json=self.create_data, timeout=10
        )
        if DEBUG:
            logger.debug(f"Create group response status code: {response.status_code}")
            logger.debug(f"Create group response text: {response.text}")
        response.raise_for_status()
        return response.status_code == 200

    @retry(
        stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=1, max=10)
    )
    def delete(self) -> bool:
        """
        Delete the Alexa group using the API.

        Returns:
            bool: True if deletion was successful, False otherwise.

        Raises:
            requests.HTTPError: If deletion fails after retries.
        """
        url = f"{URLS['DELETE_GROUP']}{self.id}"
        if DO_NOT_DELETE:
            logger.info(f"Skipping deletion of group {self.id} ({self.name})")
            return True
        response = requests.delete(url, headers=ALEXA_HEADERS, timeout=10)
        if DEBUG:
            logger.debug(f"Delete group response status code: {response.status_code}")
            logger.debug(f"Delete group response text: {response.text}")
        response.raise_for_status()
        return response.status_code == 200
