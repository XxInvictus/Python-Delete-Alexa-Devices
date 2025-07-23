"""
api.py

API and data processing functions for Alexa management script.

This module contains functions for fetching and processing data from Alexa and Home Assistant APIs.
"""

import json
from typing import Any, Dict, List
import requests
from alexa_manager.config import (
    DEBUG,
    DEBUG_FILES,
    URLS,
    ALEXA_HEADERS,
)
from alexa_manager.models import AlexaEntities, AlexaEntity, AlexaGroups, AlexaGroup
from alexa_manager.utils import rate_limited
import logging

logger = logging.getLogger(__name__)


def _safe_json_loads(text: str) -> Any:
    """
    Safely load JSON from a string, handling trailing commas and missing braces.

    Args:
        text (str): The JSON string to load.

    Returns:
        Any: The loaded JSON object.
    """
    text = text.strip()
    if text.endswith(","):
        text = text[:-1]
    if not (text.startswith("{") and text.endswith("}")):
        text = "{" + text + "}"
    return json.loads(text)


@rate_limited
def get_entities(url: str = URLS["GET_ENTITIES"]) -> AlexaEntities:
    """
    Retrieve Alexa skill entities from the specified API endpoint.

    Args:
        url (str): The API endpoint URL.

    Returns:
        AlexaEntities: A collection of AlexaEntity objects.
    """
    parameters = {"skillId": "amzn1.ask.1p.smarthome"}
    try:
        response = requests.get(
            url, headers=ALEXA_HEADERS, params=parameters, timeout=15
        )
        entities = AlexaEntities()
        if response.text.strip():
            try:
                response_json = response.json()
            except Exception as e:
                logger.error(
                    f"Error: Could not decode JSON from Alexa entities API: {e}"
                )
                return entities
            for item in response_json:
                if not all(k in item for k in ("id", "displayName", "description")):
                    logger.warning(
                        f"Warning: Skipping entity with missing keys: {item}"
                    )
                    continue
                entity = AlexaEntity(
                    entity_id=item["id"],
                    display_name=item["displayName"],
                    description=item["description"],
                )
                entities.add_entity(entity)
            if DEBUG:
                logger.debug(f"Loaded {len(entities.entities)} Alexa entities.")
        return entities
    except requests.RequestException as e:
        logger.error(f"Request error while fetching Alexa entities: {e}")
        return AlexaEntities()


@rate_limited
def get_graphql_endpoint_entities() -> AlexaEntities:
    """
    Retrieve Alexa endpoint entities using a GraphQL POST request.

    Returns:
        AlexaEntities: A collection of AlexaEntity objects from GraphQL endpoint.
    """
    url = f"https://{URLS['GET_ENTITIES'].split('/')[2]}/nexus/v1/graphql"
    data = {
        "query": """
        query CustomerSmartHome {
            endpoints(endpointsQueryParams: { paginationParams: { disablePagination: true } }) {
                items {
                    friendlyName
                    legacyAppliance {
                        applianceId
                        mergedApplianceIds
                        connectedVia
                        applianceKey
                        appliancePairs
                        modelName
                        friendlyDescription
                        version
                        friendlyName
                        manufacturerName
                    }
                }
            }
        }
        """
    }
    try:
        response = requests.post(url, headers=ALEXA_HEADERS, json=data, timeout=15)
        try:
            response_json = response.json()
        except Exception as e:
            logger.error(f"Error: Could not decode JSON from GraphQL endpoint API: {e}")
            return AlexaEntities()
        entities = AlexaEntities()
        try:
            items = response_json["data"]["endpoints"]["items"]
        except Exception as e:
            logger.error(f"Error: GraphQL response missing expected keys: {e}")
            return entities
        for item in items:
            try:
                entity = AlexaEntity(
                    entity_id=item["legacyAppliance"]["applianceKey"],
                    display_name=item["friendlyName"],
                    description=item["legacyAppliance"]["friendlyDescription"],
                    appliance_id=item["legacyAppliance"].get("applianceId", ""),
                )
                entities.add_entity(entity)
            except Exception as e:
                logger.warning(
                    f"Warning: Skipping endpoint entity with missing keys: {e}"
                )
                continue
        if DEBUG:
            with open(DEBUG_FILES["graphql"], "w", encoding="utf_8") as file:
                json.dump(response_json, file)
        return entities
    except Exception as e:
        logger.error(f"Error fetching GraphQL endpoint entities: {e}")
        return AlexaEntities()


@rate_limited
def get_groups(url: str = URLS["GET_GROUPS"]) -> AlexaGroups:
    """
    Retrieve Alexa groups from the API.

    Args:
        url (str): The API endpoint URL.

    Returns:
        AlexaGroups: A collection of AlexaGroup objects.
    """
    try:
        response = requests.get(url, headers=ALEXA_HEADERS, timeout=15)
        groups = AlexaGroups()
        if response.text.strip():
            try:
                response_json = response.json()
            except Exception as e:
                logger.error(f"Error: Could not decode JSON from Alexa groups API: {e}")
                return groups
            if "applianceGroups" not in response_json:
                logger.error(
                    "Error: 'applianceGroups' key missing in Alexa groups response."
                )
                return groups
            for item in response_json["applianceGroups"]:
                if not all(k in item for k in ("name", "groupId")):
                    logger.warning(f"Warning: Skipping group with missing keys: {item}")
                    continue
                group = AlexaGroup(name=item["name"], group_id=item["groupId"])
                groups.add_group(group)
            if DEBUG:
                with open(DEBUG_FILES["groups"], "w", encoding="utf_8") as file:
                    json.dump(response_json["applianceGroups"], file)
        else:
            logger.warning("Empty response received from server.")
        return groups
    except Exception as e:
        logger.error(f"Error fetching Alexa groups: {e}")
        return AlexaGroups()


@rate_limited
def get_ha_areas() -> Dict[str, List[str]]:
    """
    Fetch Home Assistant areas and their child entity IDs.

    Returns:
        Dict[str, List[str]]: Dictionary mapping area names to lists of entity IDs.
    """
    # Import HA_HEADERS from config only when needed to avoid issues in Alexa Only mode
    from alexa_manager.config import HA_HEADERS

    areas_template = {
        "template": "{%- for area in areas() -%} {{area|to_json}}:{{area_entities(area)|to_json}}, {%- endfor -%}"
    }
    try:
        response = requests.post(
            URLS["HA_TEMPLATE"],
            headers=HA_HEADERS,
            timeout=15,
            data=json.dumps(areas_template),
        )
        if response.status_code == 200:
            try:
                area_dict = _safe_json_loads(response.text)
                return area_dict
            except Exception as e:
                logger.error(
                    f"Error: Could not parse Home Assistant API response as JSON: {e}"
                )
                return {}
        else:
            logger.error(
                f"Failed to retrieve areas: {response.status_code} - {response.text}"
            )
            return {}
    except Exception as e:
        logger.error(f"Error fetching Home Assistant areas: {e}")
        return {}


def map_ha_entities_to_alexa_ids(
    ha_areas: Dict[str, List[str]], endpoints: AlexaEntities
) -> Dict[str, List[str]]:
    """
    Map Home Assistant entity IDs to Alexa Application IDs (applianceId) for each area.

    Args:
        ha_areas (Dict[str, List[str]]): Dictionary mapping area names to lists of HA entity IDs.
        endpoints (AlexaEntities): AlexaEntities object containing endpoint entities.

    Returns:
        Dict[str, List[str]]: Dictionary mapping area names to lists of Alexa applianceIds.
    """
    ha_to_alexa = {e.ha_entity_id: e.appliance_id for e in endpoints.entities}
    area_to_alexa_ids: Dict[str, List[str]] = {}
    for area, ha_ids in ha_areas.items():
        alexa_ids = [
            ha_to_alexa[ha_id.lower()]
            for ha_id in ha_ids
            if ha_id.lower() in ha_to_alexa
        ]
        area_to_alexa_ids[area] = alexa_ids
    return area_to_alexa_ids
