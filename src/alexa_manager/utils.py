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
