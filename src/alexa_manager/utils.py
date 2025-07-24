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


def sanitize_list(items: List[Any], key: str = None) -> List[str]:
    """
    Sanitize a list to ensure all elements are hashable strings.
    If a key is provided, extract that key from dicts or JSON strings.
    Handles dicts, JSON strings, and other types robustly.

    Args:
        items (List[Any]): The input list to sanitize.
        key (str, optional): The key to extract from dicts or JSON strings.

    Returns:
        List[str]: A list of hashable strings.
    """
    import json

    sanitized: List[str] = []
    for item in items:
        # If item is a dict and key is provided, extract key
        if isinstance(item, dict):
            if key and key in item:
                sanitized.append(str(item[key]))
            else:
                sanitized.append(str(item))
        # If item is a JSON string, try to parse and extract key
        elif isinstance(item, str):
            if key:
                try:
                    parsed = json.loads(item)
                    if isinstance(parsed, dict) and key in parsed:
                        sanitized.append(str(parsed[key]))
                    else:
                        sanitized.append(item)
                except (json.JSONDecodeError, TypeError):
                    sanitized.append(item)
            else:
                sanitized.append(item)
        else:
            sanitized.append(str(item))
    return sanitized
