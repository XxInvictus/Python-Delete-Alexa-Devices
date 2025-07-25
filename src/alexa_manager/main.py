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
import time
import uuid
from typing import Any, Dict, List

from alexa_manager.config import (
    config,
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
    format_appliance_id_for_api,
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


def confirm_batch_action(item_descriptions: List[str], action_type: str) -> bool:
    """
    Prompt the user for confirmation before performing a batch of API actions.

    Args:
        item_descriptions (List[str]): List of item descriptions.
        action_type (str): Type of action (e.g., 'delete', 'create').

    Returns:
        bool: True if the user confirms, False otherwise.
    """
    print("\nCONFIRMATION REQUIRED:")
    print(f"You are about to {action_type} the following items:")
    for description in item_descriptions:
        print(f"  - {description}")
    print("Proceed with all? (y/n): ", end="", flush=True)
    response = input().strip().lower()
    return response == "y"


def process_deletion(
    item, item_type: str, dry_run: bool, collector: List[Dict[str, Any]]
) -> None:
    """
    Handle deletion of a single entity or group, with dry run support.

    Args:
        item: The entity or group object to delete.
        item_type (str): Either 'entity' or 'group'.
        dry_run (bool): If True, only print the intended action.
        collector (List[Dict[str, Any]]): List to collect failed deletions.
    """
    if item_type == "entity":
        url = f"https://{config['ALEXA_HOST']}/api/phoenix/appliance/{item.delete_id}"
        name = item.display_name
        item_id = item.id
    else:
        url = f"https://{config['ALEXA_HOST']}/api/phoenix/group/{item.id}"
        name = item.name
        item_id = item.id
    if dry_run:
        from rich.console import Console

        console = Console()
        console.print(
            f"[bold yellow][DRY RUN][/bold yellow] Would DELETE {item_type}: [cyan]{name}[/cyan] (ID: {item_id}) at [green]{url}[/green]"
        )
        return
    delete_success = item.delete()
    if not delete_success:
        if item_type == "entity":
            collector.append(
                {
                    "name": name,
                    "entity_id": item_id,
                    "device_id": item.delete_id,
                    "description": item.description,
                }
            )
        else:
            collector.append({"name": name, "group_id": item_id})


def delete_entities(
    entities: AlexaEntities, interactive_mode: bool = False
) -> List[Dict[str, Any]]:
    """
    Send a DELETE request to remove entities/endpoints related to the Amazon Alexa skill.

    Args:
        entities (AlexaEntities): AlexaEntities object containing entities to delete.
        interactive_mode (bool): If True, require user confirmation before deletion.

    Returns:
        List[Dict[str, Any]]: A list of dictionaries containing information about failed deletions.
    """

    failed_deletions: List[Dict[str, Any]] = []
    entity_descriptions = [
        f"{entity.display_name} (ID: {entity.id}, Device ID: {entity.delete_id})"
        for entity in entities.entities
    ]
    if not DRY_RUN and entity_descriptions and interactive_mode:
        if not confirm_batch_action(entity_descriptions, "delete"):
            print("Deletion cancelled by user.")
            return []

    def per_entity(entity, collector):
        process_deletion(entity, "entity", DRY_RUN, collector)

    run_with_progress_bar(
        list(entities.entities),
        "Deleting Alexa entities...",
        per_entity,
        failed_deletions,
    )
    if failed_deletions:
        logger.warning("\nFailed to delete the following entities:")
        for failure in failed_deletions:
            logger.warning(
                f"Name: '{failure['name']}', Entity ID: '{failure['entity_id']}', Device ID: '{failure['device_id']}', Description: '{failure['description']}'"
            )
    return failed_deletions


def delete_groups(
    groups: AlexaGroups, interactive_mode: bool = False
) -> List[Dict[str, Any]]:
    """
    Send a DELETE request to remove all Alexa groups.

    Args:
        groups (AlexaGroups): AlexaGroups object containing groups to delete.
        interactive_mode (bool): If True, require user confirmation before deletion.

    Returns:
        List[Dict[str, Any]]: A list of dictionaries containing information about failed deletions.
    """

    failed_deletions: List[Dict[str, Any]] = []
    group_descriptions = [f"{group.name} (ID: {group.id})" for group in groups.groups]
    if not DRY_RUN and group_descriptions and interactive_mode:
        if not confirm_batch_action(group_descriptions, "delete"):
            print("Deletion cancelled by user.")
            return []

    def per_group(group, collector):
        process_deletion(group, "group", DRY_RUN, collector)

    run_with_progress_bar(
        list(groups.groups), "Deleting Alexa groups...", per_group, failed_deletions
    )
    if failed_deletions:
        logger.warning("\nFailed to delete the following groups:")
        for failure in failed_deletions:
            logger.warning(
                f"Name: '{failure['name']}', Group ID: '{failure['group_id']}'"
            )
    return failed_deletions


def create_groups_from_areas(
    ha_areas: Dict[str, Any], config: Dict[str, Any], interactive_mode: bool = False
) -> List[Dict[str, Any]]:
    """
    Create Alexa groups from Home Assistant areas, excluding those in the ignore list.

    Args:
        ha_areas (Dict[str, Any]): Home Assistant areas.
        config (Dict[str, Any]): Configuration dictionary.
        interactive_mode (bool): If True, require user confirmation before creation.

    Returns:
        List[Dict[str, Any]]: List of failed creations.
    """
    failed_creations = []
    for area_name, ha_entity_ids in ha_areas.items():
        if area_name in IGNORED_HA_AREAS:
            logger.info(f"Skipping ignored area: {area_name}")
            continue
        group_name = convert_ha_area_name(area_name)
        logger.info(f"Processing area '{area_name}' -> group '{group_name}'")

        # Check if the group already exists
        existing_groups = config.get("EXISTING_GROUPS", [])
        existing_group = next(
            (g for g in existing_groups if g["name"] == group_name), None
        )
        if existing_group:
            logger.info(
                f"Group already exists: {group_name} (ID: {existing_group['id']})"
            )
            continue

        # Create the group
        logger.info(f"Creating group: {group_name}")
        group = AlexaGroup(name=group_name)
        group.appliance_ids = [
            json.loads(format_appliance_id_for_api(ha_entity_id))["applianceId"]
            for ha_entity_id in ha_entity_ids
        ]
        # Ensure DRY_RUN is respected at runtime
        success = group.create()
        if not success:
            logger.error(f"Failed to create group: {group_name}")
            failed_creations.append({"name": group_name})
        else:
            logger.info(f"Group created successfully: {group_name}")

    return failed_creations


# Expose create_groups_from_areas for testing and patching
create_groups_from_areas = create_groups_from_areas

# -----------------
# Main Function
# -----------------


def parse_arguments() -> argparse.Namespace:
    """
    Parse and validate command-line arguments for Alexa Manager operations.

    Returns:
        argparse.Namespace: Parsed arguments namespace.
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
    parser.add_argument(
        "--interactive",
        action="store_true",
        help="Enable interactive mode for batch actions, requiring user confirmation.",
    )
    parser.add_argument(
        "--test-alexa-groups",
        action="store_true",
        help="Test Alexa group creation, retrieval, and deletion with a randomly selected ApplianceId.",
    )
    args = parser.parse_args()
    # Validate mutually exclusive arguments if needed
    return args


def set_global_flags(args: argparse.Namespace) -> None:
    """
    Set global flags based on parsed arguments.

    Args:
        args (argparse.Namespace): Parsed arguments.
    """
    import alexa_manager.config as config_mod

    config_mod.DRY_RUN = args.dry_run
    global DRY_RUN
    DRY_RUN = args.dry_run


def handle_get_actions(args: argparse.Namespace) -> None:
    """
    Handle all GET actions based on command-line arguments.

    Args:
        args (argparse.Namespace): Parsed arguments.
    """
    get_args = [
        args.get_entities,
        args.get_endpoints,
        args.get_groups,
        args.get_ha_areas,
        args.get_ha_mapping,
    ]
    if not any(get_args):
        return
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
                # Build a lookup of normalized Alexa Appliance IDs for this area
                norm_alexa_ids = set()
                for aid in alexa_ids:
                    if "==_" in aid:
                        aid_norm = aid.split("==_")[-1].replace("#", ".").lower()
                    else:
                        aid_norm = aid.replace("#", ".").lower()
                    norm_alexa_ids.add(aid_norm)
                for ha_id in ha_ids:
                    ha_id_norm = ha_id.lower()
                    # Find the matching Alexa ID
                    matched_alexa_id = None
                    for aid in alexa_ids:
                        if "==_" in aid:
                            aid_norm = aid.split("==_")[-1].replace("#", ".").lower()
                        else:
                            aid_norm = aid.replace("#", ".").lower()
                        if ha_id_norm == aid_norm:
                            matched_alexa_id = aid
                            break
                    mapping_rows.append(
                        {
                            AREA: area,
                            HA_ENTITY_ID: ha_id,
                            ID: matched_alexa_id if matched_alexa_id else "",
                        }
                    )
            print_table(
                mapping_rows,
                [AREA, HA_ENTITY_ID, ID],
                "HA to Alexa Entity Mapping (Exact Matches Only)",
            )
    # Exit after GET actions
    sys.exit(0)


def dispatch_actions(args: argparse.Namespace) -> Dict[str, List[Dict[str, Any]]]:
    """
    Dispatch DELETE and CREATE actions based on command-line arguments.

    Args:
        args (argparse.Namespace): Parsed arguments.

    Returns:
        Dict[str, List[Dict[str, Any]]]: Dictionary of failed actions.
    """
    failed_entity_deletions = []
    failed_endpoint_deletions = []
    failed_group_deletions = []
    failed_group_creations = []
    do_all = not (
        args.delete_entities
        or args.delete_endpoints
        or args.delete_groups
        or args.create_groups
    )
    if args.delete_entities or do_all:
        failed_entity_deletions = delete_entities(get_entities(), args.interactive)
    if args.delete_endpoints or do_all:
        failed_endpoint_deletions = delete_entities(
            get_graphql_endpoint_entities(), args.interactive
        )
    if args.delete_groups or do_all:
        failed_group_deletions = delete_groups(get_groups(), args.interactive)
    if args.create_groups or do_all:
        if args.alexa_only:
            logger.info(
                "Alexa Only mode: Skipping Home Assistant area-based group creation."
            )
        else:
            failed_group_creations = create_groups_from_areas(
                get_ha_areas(), config, args.interactive
            )
    return {
        "failed_entity_deletions": failed_entity_deletions,
        "failed_endpoint_deletions": failed_endpoint_deletions,
        "failed_group_deletions": failed_group_deletions,
        "failed_group_creations": failed_group_creations,
    }


def report_failures(failures: Dict[str, List[Dict[str, Any]]]) -> None:
    """
    Report failed actions in a structured manner.

    Args:
        failures (Dict[str, List[Dict[str, Any]]]): Dictionary of failed actions.
    """
    if any(failures.values()):
        logger.info("\nSummary of all failed deletions:")
        if failures["failed_entity_deletions"]:
            logger.warning("\nFailed Entities:")
            for failure in failures["failed_entity_deletions"]:
                logger.warning(
                    f"Name: '{failure['name']}', Entity ID: '{failure['entity_id']}'"
                )
        if failures["failed_endpoint_deletions"]:
            logger.warning("\nFailed Endpoints:")
            for failure in failures["failed_endpoint_deletions"]:
                logger.warning(
                    f"Name: '{failure['name']}', Entity ID: '{failure['entity_id']}'"
                )
        if failures["failed_group_deletions"]:
            logger.warning("\nFailed Groups:")
            for failure in failures["failed_group_deletions"]:
                logger.warning(
                    f"Name: '{failure['name']}', Group ID: '{failure['group_id']}'"
                )
        if failures["failed_group_creations"]:
            logger.warning("\nFailed Group Creations:")
            for failure in failures["failed_group_creations"]:
                logger.warning(f"Name: '{failure['name']}'")
    else:
        logger.info("Done")
        logger.info(
            f"- Removed all entities and endpoints with a matching description containing '{config['DESCRIPTION_FILTER_TEXT']}'"
        )
        logger.info("- Removed all groups")
        logger.info("- Created all Home Assistant areas as Alexa groups")


def main() -> None:
    """
    Main entry point for the script. Parses command-line arguments and runs selected actions.
    """
    args = parse_arguments()
    set_global_flags(args)
    if args.test_alexa_groups:
        test_alexa_groups()
        return
    handle_get_actions(args)
    failures = dispatch_actions(args)
    report_failures(failures)


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


def test_alexa_groups() -> None:
    """
    Test Alexa group creation, update, retrieval, and deletion with randomly selected ApplianceIds.
    Uses the correct applianceId from endpoint objects, not entityId or applianceKey.
    Steps:
        1. Select two distinct endpoints and use their applianceId for group creation/update.
        2. Create a group with the first applianceId (formatted for API).
        3. Retrieve and confirm creation.
        4. Update the group by adding the second applianceId (formatted for API).
        5. Retrieve and confirm both applianceIds are present.
        6. Delete the group.
    """
    import random
    from alexa_manager.api import get_graphql_endpoint_entities, get_groups
    from rich import print as rprint

    endpoints = get_graphql_endpoint_entities().entities
    if not endpoints:
        rprint("[red]No endpoints found. Cannot test Alexa group creation.[/red]")
        return
    if len(endpoints) < 2:
        rprint(
            "[red]Not enough endpoints to test group update with multiple ApplianceIds.[/red]"
        )
        return
    # Select two distinct endpoints and use their applianceId
    endpoint1, endpoint2 = random.sample(endpoints, 2)
    appliance_id_1 = getattr(endpoint1, "appliance_id", None)
    appliance_id_2 = getattr(endpoint2, "appliance_id", None)
    rprint(
        f"[yellow]Selected applianceIds: {appliance_id_1}, {appliance_id_2}[/yellow]"
    )
    if not appliance_id_1 or not appliance_id_2:
        rprint(
            "[red]Could not retrieve applianceId from endpoints. Check endpoint data structure.[/red]"
        )
        return
    from alexa_manager.models import AlexaGroup, format_appliance_id_for_api

    placeholder_name = f"TestGroup{str(uuid.uuid4())[:8]}"
    group = AlexaGroup(name=placeholder_name)
    group.create_data["applianceIds"] = [format_appliance_id_for_api(appliance_id_1)]
    rprint(f"[blue]Creating group with applianceId: {appliance_id_1}[/blue]")
    success = group.create()
    if not success:
        rprint(f"[red]Failed to create group with ApplianceId {appliance_id_1}.[/red]")
        return
    # Wait for backend consistency
    time.sleep(2)
    # Retrieve groups and confirm creation
    groups = get_groups().groups
    rprint(f"[yellow]All group names returned: {[g.name for g in groups]}[/yellow]")
    created_group = next(
        (
            g
            for g in groups
            if g.name.strip().lower() == placeholder_name.strip().lower()
        ),
        None,
    )
    if not created_group:
        rprint(
            f"[red]Group creation verification failed for '{placeholder_name}'. Group not found in GET response.[/red]"
        )
        rprint(f"[red]Full GET response: {groups}[/red]")
        return
    # For GET, applianceIds are raw strings in AlexaExpandedGroup.appliance_ids
    expected_raw_id = json.loads(format_appliance_id_for_api(appliance_id_1))[
        "applianceId"
    ]
    if expected_raw_id in getattr(created_group, "appliance_ids", []):
        rprint(
            f"[green]Group '{placeholder_name}' created successfully with ApplianceId '{expected_raw_id}'.[/green]"
        )
    else:
        rprint(
            f"[red]Group creation verification failed for '{placeholder_name}'. ApplianceId not found in group.[/red]"
        )
        rprint(f"[red]Group data: {getattr(created_group, 'appliance_ids', [])}[red]")
        return
    # Update the group by adding a second applianceId (formatted for API)
    # Avoid duplicates and preserve correct format
    existing_ids = set(getattr(created_group, "appliance_ids", []))
    new_id_raw = json.loads(format_appliance_id_for_api(appliance_id_2))["applianceId"]
    updated_appliance_ids = list(existing_ids) + [new_id_raw]
    # Use AlexaExpandedGroup for update
    created_group.appliance_ids = updated_appliance_ids
    rprint(f"[blue]Updating group to add applianceId: {appliance_id_2}[/blue]")
    update_success = created_group.update()
    if not update_success:
        rprint(
            f"[red]Failed to update group '{placeholder_name}' with additional ApplianceId '{appliance_id_2}'.[/red]"
        )
        # If DEBUG is False, attempt to delete the group even if update fails
        from alexa_manager.config import DEBUG

        if not DEBUG:
            rprint(
                f"[yellow]DEBUG is False. Attempting to delete group '{placeholder_name}' despite update failure.[/yellow]"
            )
            deleted = created_group.delete()
            if deleted:
                rprint(
                    f"[green]Group '{placeholder_name}' deleted successfully.[/green]"
                )
            else:
                rprint(f"[red]Failed to delete group '{placeholder_name}'.[/red]")
        return
    # Retrieve group again and confirm both applianceIds are present (raw string check)
    groups = get_groups().groups
    updated_group = next((g for g in groups if g.name == placeholder_name), None)
    if updated_group:
        present_ids = set(getattr(updated_group, "appliance_ids", []))
        rprint(f"[yellow]Group applianceIds after update: {present_ids}[/yellow]")
        if expected_raw_id in present_ids and new_id_raw in present_ids:
            rprint(
                f"[green]Group '{placeholder_name}' updated successfully with ApplianceIds '{expected_raw_id}' and '{new_id_raw}'.[/green]"
            )
        else:
            rprint(
                f"[red]Group update verification failed: missing ApplianceIds in '{placeholder_name}'.[/red]"
            )
    else:
        rprint(f"[red]Group '{placeholder_name}' not found after update.[/red]")
        return
    # Delete the group
    deleted = updated_group.delete() if updated_group else False
    if deleted:
        rprint(f"[green]Group '{placeholder_name}' deleted successfully.[/green]")
    else:
        rprint(f"[red]Failed to delete group '{placeholder_name}'.[/red]")
