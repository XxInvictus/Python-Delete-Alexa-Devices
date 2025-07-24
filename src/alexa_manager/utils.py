"""
utils.py

Utility functions for Alexa management script.

This module contains helper functions such as rate limiting, progress bar, and table printing.
"""

import functools
import time
from typing import Any, Callable, List
from alexa_manager.config import SHOULD_SLEEP
import logging


def rate_limited(func: Callable) -> Callable:
    """
    Decorator to apply a rate limit to a function using time.sleep.

    Args:
        func (Callable): The function to be rate limited.

    Returns:
        Callable: The wrapped function with rate limiting applied.
    """
    RATE_LIMIT_SLEEP = 0.2

    @functools.wraps(func)
    def wrapper(*args, **kwargs):
        if SHOULD_SLEEP:
            time.sleep(RATE_LIMIT_SLEEP)
        return func(*args, **kwargs)

    return wrapper


def run_with_progress_bar(
    items: List[Any],
    description: str,
    per_item_func: Callable,
    fail_collector: List[Any],
) -> None:
    """
    Run a batch operation with a progress bar and interrupt handling.

    Args:
        items (List[Any]): Items to process.
        description (str): Description for the progress bar.
        per_item_func (Callable): Function to run for each item.
        fail_collector (List[Any]): Collector for failed items.

    Returns:
        None
    """
    logger = logging.getLogger(__name__)
    try:
        from rich.progress import Progress

        with Progress() as progress:
            task = progress.add_task(description, total=len(items))
            for item in items:
                try:
                    per_item_func(item, fail_collector)
                except KeyboardInterrupt:
                    logger.warning(
                        f"Interrupted during {description.lower()}. Partial progress will be reported."
                    )
                    break
                finally:
                    progress.update(task, advance=1)
    except ImportError:
        # Fallback if rich is not installed
        for item in items:
            try:
                per_item_func(item, fail_collector)
            except KeyboardInterrupt:
                logger.warning(
                    f"Interrupted during {description.lower()}. Partial progress will be reported."
                )
                break


def print_table(data: List[dict], columns: List[str], title: str) -> None:
    """
    Print a table of data in the console using rich if available.

    Args:
        data (List[dict]): List of row data.
        columns (List[str]): List of column names.
        title (str): Title for the table.

    Returns:
        None
    """
    try:
        from rich.console import Console
        from rich.table import Table
    except ImportError:
        print(
            "Error: The 'rich' library is required for pretty console output. Install it with 'uv add rich'."
        )
        return
    console = Console()
    table = Table(title=title)
    for col in columns:
        table.add_column(col)
    for row in data:
        table.add_row(*[str(row.get(col, "")) for col in columns])
    if not data:
        console.print(f"[yellow]No {title.lower()} found.[/yellow]")
    else:
        console.print(table)


def convert_ha_area_name(area_name: str) -> str:
    """
    Convert a Home Assistant Area name for Alexa Group comparison/use.

    Replaces underscores with spaces and converts to Title Case.
    Handles edge cases such as empty strings and multiple underscores.

    Args:
        area_name (str): The original HA Area name.

    Returns:
        str: The converted Area name in Title Case with spaces.
    """
    if not isinstance(area_name, str):
        raise TypeError("area_name must be a string")
    # Replace underscores with spaces, strip leading/trailing spaces, and convert to Title Case
    return area_name.replace("_", " ").strip().title()


def normalize_area_name(area_name: str) -> str:
    """
    Normalize area names for comparison between HA and Alexa formats.
    Converts to lowercase, replaces underscores with spaces, and strips whitespace.

    Args:
        area_name (str): The area name to normalize.

    Returns:
        str: Normalized area name.
    """
    return area_name.replace("_", " ").strip().lower()


def sanitize_list(input_list: list, key: str = None) -> list:
    """
    Sanitize a list to ensure all items are hashable (strings).
    If a dict is found, extract the value for 'key' if provided, else str(dict).
    """
    sanitized = []
    for item in input_list:
        if isinstance(item, dict):
            val = item.get(key) if key and key in item else str(item)
            sanitized.append(val)
            logging.warning(f"Sanitized dict in list: {item} -> {val}")
        else:
            sanitized.append(str(item))
    return sanitized


def flatten_dict(d: dict) -> dict:
    """
    Recursively convert all nested dicts to strings for hashability.
    This ensures that any dict, even if deeply nested, is converted to a string.
    """
    if not isinstance(d, dict):
        return d
    flat = {}
    for k, v in d.items():
        if isinstance(v, dict):
            flat[k] = str(flatten_dict(v))
        elif isinstance(v, list):
            flat[k] = [
                str(flatten_dict(item)) if isinstance(item, dict) else item
                for item in v
            ]
        else:
            flat[k] = v
    return flat


def format_appliance_id_for_api(appliance_id: str) -> str:
    """
    Format the appliance ID for Alexa API requests.

    Parameters:
    appliance_id (str): The raw appliance ID string.

    Returns:
    str: A JSON string formatted for the Alexa API, e.g. '{"applianceId": "..."}'.
    """
    import json

    if not appliance_id or not isinstance(appliance_id, str):
        raise ValueError("appliance_id must be a non-empty string")
    return json.dumps({"applianceId": appliance_id})


def _dry_run_action(action: str, target: str, url: str, extra: str = "") -> None:
    """
    Helper to print dry-run actions for entities and groups.
    Args:
        action (str): The action being simulated (e.g., 'DELETE', 'CREATE').
        target (str): The name or ID of the target entity/group.
        url (str): The API endpoint URL.
        extra (str): Additional info to print (optional).
    """
    from rich.console import Console

    console = Console()
    msg = f"[bold yellow][DRY RUN][/bold yellow] Would {action} {target} at [green]{url}[/green]"
    if extra:
        msg += f" {extra}"
    console.print(msg)
