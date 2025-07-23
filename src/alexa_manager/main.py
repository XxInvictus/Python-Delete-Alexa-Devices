"""
main.py

This script provides utilities to interact with the Amazon Alexa API for managing skill-related entities and endpoints.

Main Functions:
    - get_entities: Retrieves Alexa skill entities via a GET request.
    - delete_entities: Deletes Alexa skill entities via DELETE requests.
    - get_graphql_endpoints: Retrieves endpoint properties using a GraphQL POST request.
    - delete_endpoints: Deletes endpoints via DELETE requests.

The script uses global headers and parameters for requests, and can be run as a standalone file to sequentially retrieve and delete entities and endpoints.
"""

import argparse
import json
import logging
import sys
from typing import Any, Dict, List

from alexa_manager.config import (
    config,
    DRY_RUN,
    IGNORED_HA_AREAS,
)
from alexa_manager.models import (
    AlexaEntities,
    AlexaGroups,
    AlexaGroup,
)
from alexa_manager.utils import (
    run_with_progress_bar,
    print_table,
    convert_ha_area_name,
    normalize_area_name,
)
from alexa_manager.api import (
    get_entities,
    get_graphql_endpoint_entities,
    get_groups,
    get_ha_areas,
    map_ha_entities_to_alexa_ids,
)

logger = logging.getLogger(__name__)


def setup_initial_logging() -> None:
    """
    Set up a basic logging configuration at INFO level for early-stage logging.
    This allows logging before the config file is loaded. The log level will be
    updated after loading the config.
    """
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s: %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )


def update_logging_level(debug: bool) -> None:
    """
    Update the logging level based on the debug flag from the config.

    Parameters:
    debug (bool): If True, set logging to DEBUG; otherwise, INFO.
    """
    level = logging.DEBUG if debug else logging.INFO
    logging.getLogger().setLevel(level)


# Set up logging
logging.basicConfig(
    level=logging.DEBUG if config["DEBUG"] else logging.INFO,
    format="%(asctime)s %(levelname)s: %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logging.basicConfig(level=logging.DEBUG)  # Force debug output to console

# Table header constants
ID = "ID"
DISPLAY_NAME = "Display Name"
HA_ENTITY_ID = "HA Entity ID"
DESCRIPTION = "Description"
GROUP_ID = "Group ID"
NAME = "Name"
ALEXA_APPLIANCE_ID = "Alexa Appliance ID"
AREA = "Area"

# ------------------
# Action Functions
# ------------------


def create_groups_from_areas(ha_areas: Dict[str, Any], config: Dict[str, Any]) -> List[Dict[str, Any]]:
    """
    Create Alexa groups from Home Assistant areas, excluding those in the ignore list.

    Args:
        ha_areas (Dict[str, Any]): Home Assistant areas.
        config (Dict[str, Any]): Configuration dictionary.

    Returns:
        List[Dict[str, Any]]: List of failed creations.
    """
    # Filter out ignored areas using normalized names (already normalized in config.py)
    from alexa_manager.utils import normalize_area_name
    filtered_areas = {
        k: v for k, v in ha_areas.items()
        if normalize_area_name(k) not in IGNORED_HA_AREAS
    }
    failed_creations: List[Dict[str, Any]] = []
    endpoints = get_graphql_endpoint_entities()
    area_to_alexa_ids = map_ha_entities_to_alexa_ids(filtered_areas, endpoints)

    def per_area(area_name: str, collector: List[Dict[str, Any]]):
        alexa_ids = area_to_alexa_ids.get(area_name, [])
        appliance_ids = [json.dumps({"applianceId": aid}) for aid in alexa_ids]
        converted_name = convert_ha_area_name(area_name)
        group = AlexaGroup(name=converted_name)
        group.create_data["applianceIds"] = appliance_ids
        if DRY_RUN:
            from rich.console import Console
            console = Console()
            console.print(f"[bold yellow][DRY RUN][/bold yellow] Would CREATE group: [cyan]{group.name}[/cyan] with appliance IDs: [green]{appliance_ids}[/green]")
            return
        create_success = group.create()
        if not create_success:
            collector.append({"name": group.name})

    run_with_progress_bar(
        list(filtered_areas.keys()),
        "Creating Alexa groups from HA areas...",
        per_area,
        failed_creations,
    )
    if failed_creations:
        logger.warning("\nFailed to create the following groups:")
        for failure in failed_creations:
            logger.warning(f"Name: '{failure['name']}'")
    return failed_creations


def delete_entities(entities: AlexaEntities) -> List[Dict[str, Any]]:
    """
    Send a DELETE request to remove entities/endpoints related to the Amazon Alexa skill.

    Args:
        entities (AlexaEntities): AlexaEntities object containing entities to delete.

    Returns:
        List[Dict[str, Any]]: A list of dictionaries containing information about failed deletions.
    """
    from alexa_manager.config import DRY_RUN
    failed_deletions: List[Dict[str, Any]] = []
    def per_entity(entity, collector):
        url = f"https://{config['ALEXA_HOST']}/api/phoenix/appliance/{entity.delete_id}"
        if DRY_RUN:
            from rich.console import Console
            console = Console()
            console.print(
                f"[bold yellow][DRY RUN][/bold yellow] Would DELETE entity: [cyan]{entity.display_name}[/cyan] (ID: {entity.id}) at [green]{url}[/green]"
            )
            return
        delete_success = entity.delete()
        if not delete_success:
            collector.append(
                {
                    "name": entity.display_name,
                    "entity_id": entity.id,
                    "device_id": entity.delete_id,
                    "description": entity.description,
                }
            )
    run_with_progress_bar(
        entities.entities, "Deleting Alexa entities...", per_entity, failed_deletions
    )
    if failed_deletions:
        logger.warning("\nFailed to delete the following entities:")
        for failure in failed_deletions:
            logger.warning(
                f"Name: '{failure['name']}', Entity ID: '{failure['entity_id']}', Device ID: '{failure['device_id']}', Description: '{failure['description']}'"
            )
    return failed_deletions


def delete_groups(groups: AlexaGroups) -> List[Dict[str, Any]]:
    """
    Send a DELETE request to remove all Alexa groups.

    Args:
        groups (AlexaGroups): AlexaGroups object containing groups to delete.

    Returns:
        List[Dict[str, Any]]: A list of dictionaries containing information about failed deletions.
    """
    from alexa_manager.config import DRY_RUN
    failed_deletions: List[Dict[str, Any]] = []
    def per_group(group, collector):
        url = f"https://{config['ALEXA_HOST']}/api/phoenix/group/{group.id}"
        if DRY_RUN:
            from rich.console import Console
            console = Console()
            console.print(f"[bold yellow][DRY RUN][/bold yellow] Would DELETE group: [cyan]{group.name}[/cyan] (ID: {group.id}) at [green]{url}[/green]")
            return
        delete_success = group.delete()
        if not delete_success:
            collector.append({"name": group.name, "group_id": group.id})
    run_with_progress_bar(
        groups.groups, "Deleting Alexa groups...", per_group, failed_deletions
    )
    if failed_deletions:
        logger.warning("\nFailed to delete the following groups:")
        for failure in failed_deletions:
            logger.warning(f"Name: '{failure['name']}', Group ID: '{failure['group_id']}'")
    return failed_deletions


# -----------------
# Main Function
# -----------------


def main() -> None:
    """
    Main entry point for the script. Parses command-line arguments and runs selected actions.

    Returns:
        None
    """
    parser = argparse.ArgumentParser(
        description="Manage Alexa skill entities, endpoints, and groups.",
        epilog="""
Examples:
  python main.py --delete-entities --delete-groups
  python main.py --create-groups
  python main.py --get-entities
  python main.py --get-endpoints
  python main.py --get-groups
  python main.py --get-ha-areas
  python main.py --get-ha-mapping
  python main.py  # (runs all actions)
        """,
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument(
        "--delete-entities",
        action="store_true",
        help="Delete Alexa skill entities that match the configured filter.",
    )
    parser.add_argument(
        "--delete-endpoints",
        action="store_true",
        help="Delete Alexa GraphQL endpoints (devices/endpoints discovered via GraphQL).",
    )
    parser.add_argument(
        "--delete-groups", action="store_true", help="Delete all Alexa groups."
    )
    parser.add_argument(
        "--create-groups",
        action="store_true",
        help="Create Alexa groups for each Home Assistant area.",
    )
    parser.add_argument(
        "--get-entities",
        action="store_true",
        help="Output Alexa skill entities as a table.",
    )
    parser.add_argument(
        "--get-endpoints",
        action="store_true",
        help="Output Alexa GraphQL endpoints as a table.",
    )
    parser.add_argument(
        "--get-groups", action="store_true", help="Output Alexa groups as a table."
    )
    parser.add_argument(
        "--get-ha-areas",
        action="store_true",
        help="Output Home Assistant areas as a table.",
    )
    parser.add_argument(
        "--get-ha-mapping",
        action="store_true",
        help="Output mapping of HA entity IDs to Alexa Application IDs for each area.",
    )
    parser.add_argument(
        "--alexa-only",
        action="store_true",
        help="Run in Alexa Only mode (skip all Home Assistant dependent steps).",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Show what would be performed without making any changes. Only GET requests are executed; DELETE, PUT, POST actions are mocked and displayed.",
    )
    args = parser.parse_args()
    # Set global dry-run flag
    import alexa_manager.config as config_mod

    config_mod.DRY_RUN = args.dry_run
    global DRY_RUN
    DRY_RUN = args.dry_run

    alexa_only = args.alexa_only

    # If any get-* argument is used, only perform those gets and output results, and exit immediately
    get_args = [
        args.get_entities,
        args.get_endpoints,
        args.get_groups,
        args.get_ha_areas,
        args.get_ha_mapping,
    ]
    if any(get_args):
        if args.get_entities:
            entities = get_entities()
            print_table(
                [
                    {
                        ID: e.id,
                        DISPLAY_NAME: e.display_name,
                        HA_ENTITY_ID: e.ha_entity_id,
                        DESCRIPTION: e.description,
                    }
                    for e in entities.entities
                ],
                [ID, DISPLAY_NAME, HA_ENTITY_ID, DESCRIPTION],
                "Alexa Skill Entities",
            )
        if args.get_endpoints:
            endpoints = get_graphql_endpoint_entities()
            print_table(
                [
                    {
                        ID: e.id,
                        DISPLAY_NAME: e.display_name,
                        HA_ENTITY_ID: e.ha_entity_id,
                        DESCRIPTION: e.description,
                    }
                    for e in endpoints.entities
                ],
                [ID, DISPLAY_NAME, HA_ENTITY_ID, DESCRIPTION],
                "Alexa GraphQL Endpoints",
            )
        if args.get_groups:
            groups = get_groups()
            print_table(
                [{GROUP_ID: g.id, NAME: g.name} for g in groups.groups],
                [GROUP_ID, NAME],
                "Alexa Groups",
            )
        if args.get_ha_areas or args.get_ha_mapping:
            ha_areas = get_ha_areas()
            if args.get_ha_areas:
                print_table(
                    [
                        {NAME: area, "HA Entity IDs": ", ".join(ids)}
                        for area, ids in ha_areas.items()
                    ],
                    [NAME, "HA Entity IDs"],
                    "Home Assistant Areas",
                )
            if args.get_ha_mapping:
                endpoints = get_graphql_endpoint_entities()
                area_to_alexa_ids = map_ha_entities_to_alexa_ids(ha_areas, endpoints)
                mapping_rows = []
                for area, ha_ids in ha_areas.items():
                    alexa_ids = area_to_alexa_ids.get(area, [])
                    for ha_id, alexa_id in zip(ha_ids, alexa_ids):
                        mapping_rows.append(
                            {
                                AREA: area,
                                HA_ENTITY_ID: ha_id,
                                ALEXA_APPLIANCE_ID: alexa_id,
                            }
                        )
                print_table(
                    mapping_rows,
                    [AREA, HA_ENTITY_ID, ALEXA_APPLIANCE_ID],
                    "HA Entity to Alexa Appliance Mapping",
                )
        return

    # If no get-* arguments are given, perform all actions (default behavior)
    do_all = not (
        args.delete_entities
        or args.delete_endpoints
        or args.delete_groups
        or args.create_groups
    )

    failed_entity_deletions = []
    failed_endpoint_deletions = []
    failed_group_deletions = []
    failed_group_creations = []

    if args.delete_entities or do_all:
        failed_entity_deletions = delete_entities(get_entities())
    if args.delete_endpoints or do_all:
        failed_endpoint_deletions = delete_entities(get_graphql_endpoint_entities())
    if args.delete_groups or do_all:
        failed_group_deletions = delete_groups(get_groups())
    if args.create_groups or do_all:
        if alexa_only:
            logger.info(
                "Alexa Only mode: Skipping Home Assistant area-based group creation."
            )
        else:
            failed_group_creations = create_groups_from_areas(get_ha_areas(), config)

    if (
        failed_entity_deletions
        or failed_endpoint_deletions
        or failed_group_deletions
        or failed_group_creations
    ):
        logger.info("\nSummary of all failed deletions:")
        if failed_entity_deletions:
            logger.warning("\nFailed Entities:")
            for failure in failed_entity_deletions:
                logger.warning(
                    f"Name: '{failure['name']}', Entity ID: '{failure['entity_id']}'"
                )
        if failed_endpoint_deletions:
            logger.warning("\nFailed Endpoints:")
            for failure in failed_endpoint_deletions:
                logger.warning(
                    f"Name: '{failure['name']}', Entity ID: '{failure['entity_id']}'"
                )
        if failed_group_deletions:
            logger.warning("\nFailed Groups:")
            for failure in failed_group_deletions:
                logger.warning(
                    f"Name: '{failure['name']}', Group ID: '{failure['group_id']}'"
                )
        if failed_group_creations:
            logger.warning("\nFailed Group Creations:")
            for failure in failed_group_creations:
                logger.warning(f"Name: '{failure['name']}'")
    else:
        logger.info("Done")
        logger.info(
            f"- Removed all entities and endpoints with a matching description containing '{config['DESCRIPTION_FILTER_TEXT']}'"
        )
        logger.info("- Removed all groups")
        logger.info("- Created all Home Assistant areas as Alexa groups")


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        logger.warning(
            "\nGraceful shutdown: Operation interrupted by user. Partial progress may have been made."
        )
        sys.exit(1)
    except Exception as e:
        logger.error(f"\nFatal error in main execution: {e}")
        import traceback

        traceback.print_exc()
        sys.exit(1)
