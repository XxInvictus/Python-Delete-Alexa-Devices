"""
Unit tests for utils.py.

Covers: rate_limited decorator, run_with_progress_bar, and print_table.
"""

import time
from alexa_manager.utils import rate_limited


def test_rate_limited_decorator(monkeypatch):
    """
    Test that rate_limited decorator delays function execution when SHOULD_SLEEP is True.

    This test patches the config module and time.sleep, then reloads the utils module
    to ensure the decorator reads the patched value at runtime. This approach ensures
    the decorator's behavior is tested as it would be in production.
    """
    import sys

    # Patch config.SHOULD_SLEEP before importing utils
    import alexa_manager.config as config_module

    monkeypatch.setattr(config_module, "SHOULD_SLEEP", True)
    # Remove utils from sys.modules to force reload
    sys.modules.pop("alexa_manager.utils", None)
    import alexa_manager.utils as utils_module

    called = {}

    def fake_sleep(secs):
        called["slept"] = secs

    monkeypatch.setattr(time, "sleep", fake_sleep)

    @utils_module.rate_limited
    def foo(x):
        return x + 1

    result = foo(1)
    assert result == 2
    assert called["slept"] == 0.2


def test_rate_limited_no_sleep(monkeypatch):
    """
    Test that rate_limited decorator does not delay when SHOULD_SLEEP is False.
    """
    monkeypatch.setattr("alexa_manager.config.SHOULD_SLEEP", False)

    @rate_limited
    def foo(x):
        return x * 2

    result = foo(3)
    assert result == 6


def test_run_with_progress_bar_runs(monkeypatch):
    """
    Test run_with_progress_bar runs per_item_func for all items.
    """
    from alexa_manager.utils import run_with_progress_bar

    items = [1, 2, 3]
    called = []

    def per_item_func(item, collector):
        called.append(item)

    run_with_progress_bar(items, "Test", per_item_func, [])
    assert called == items


def test_print_table_runs():
    """
    Test print_table runs without error for simple data.
    """
    from alexa_manager.utils import print_table

    data = [{"A": 1, "B": 2}, {"A": 3, "B": 4}]
    print_table(data, ["A", "B"], "Test Table")
