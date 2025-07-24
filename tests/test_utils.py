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
    import alexa_manager.config as config_module

    monkeypatch.setattr(config_module, "SHOULD_SLEEP", True)
    sys.modules.pop("alexa_manager.utils", None)
    import alexa_manager.utils as utils_module

    sleep_called = {}

    def mock_sleep(seconds):
        sleep_called["slept"] = seconds

    monkeypatch.setattr(time, "sleep", mock_sleep)

    @utils_module.rate_limited
    def increment_value(input_value: int) -> int:
        return input_value + 1

    result = increment_value(1)
    assert result == 2
    assert sleep_called["slept"] == 0.2


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


def test_rate_limited_exception_propagation(monkeypatch):
    """
    Test that exceptions raised in the decorated function propagate correctly.
    """
    monkeypatch.setattr("alexa_manager.config.SHOULD_SLEEP", True)

    @rate_limited
    def foo(x):
        raise ValueError("Test error")

    try:
        foo(1)
    except ValueError as e:
        assert str(e) == "Test error"
    else:
        assert False, "Exception did not propagate"


def test_rate_limited_multiple_calls(monkeypatch):
    """
    Test that rate_limited decorator applies sleep for multiple calls.
    """
    import sys
    import time
    import alexa_manager.config as config_module

    monkeypatch.setattr(config_module, "SHOULD_SLEEP", True)
    sys.modules.pop("alexa_manager.utils", None)
    import alexa_manager.utils as utils_module

    sleep_calls = []

    def fake_sleep(secs):
        sleep_calls.append(secs)

    monkeypatch.setattr(time, "sleep", fake_sleep)

    @utils_module.rate_limited
    def foo(x):
        return x

    for i in range(3):
        foo(i)
    assert sleep_calls == [0.2, 0.2, 0.2]


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


def test_run_with_progress_bar_empty(monkeypatch):
    """
    Test run_with_progress_bar with empty items list.
    Should not call per_item_func and should not error.
    """
    from alexa_manager.utils import run_with_progress_bar

    items = []
    called = []

    def per_item_func(item, collector):
        called.append(item)

    run_with_progress_bar(items, "Empty Test", per_item_func, [])
    assert called == []


def test_run_with_progress_bar_large(monkeypatch):
    """
    Test run_with_progress_bar with a large list of items.
    Should process all items without error.
    """
    from alexa_manager.utils import run_with_progress_bar

    items = list(range(1000))
    called = []

    def per_item_func(item, collector):
        called.append(item)

    run_with_progress_bar(items, "Large Test", per_item_func, [])
    assert called == items


def test_run_with_progress_bar_exception(monkeypatch):
    """
    Test run_with_progress_bar when per_item_func raises an exception.
    Should propagate the exception.
    """
    from alexa_manager.utils import run_with_progress_bar

    items = [1, 2, 3]

    def per_item_func(item, collector):
        if item == 2:
            raise RuntimeError("fail")

    try:
        run_with_progress_bar(items, "Exception Test", per_item_func, [])
    except RuntimeError as e:
        assert str(e) == "fail"
    else:
        assert False, "Exception did not propagate"


def test_print_table_runs():
    """
    Test print_table runs without error for simple data.
    """
    from alexa_manager.utils import print_table

    data = [{"A": 1, "B": 2}, {"A": 3, "B": 4}]
    print_table(data, ["A", "B"], "Test Table")


def test_print_table_empty():
    """
    Test print_table with empty data and columns.
    Should not raise an error.
    """
    from alexa_manager.utils import print_table

    print_table([], [], "Empty Table")


def test_print_table_missing_columns():
    """
    Test print_table with missing columns in data.
    Should not raise an error and should handle gracefully.
    """
    from alexa_manager.utils import print_table

    data = [{"A": 1}, {"B": 2}]
    print_table(data, ["A", "B", "C"], "Missing Columns Table")


def test_print_table_non_dict_data():
    """
    Test print_table with non-dict data (should handle gracefully).
    """
    from alexa_manager.utils import print_table

    data = [1, 2, 3]
    try:
        print_table(data, ["A"], "Non-Dict Table")
    except Exception:
        assert False, "print_table should not raise error for non-dict data"


def test_print_table_large():
    """
    Test print_table with a very large table.
    Should not raise an error.
    """
    from alexa_manager.utils import print_table

    data = [{"A": i, "B": i * 2} for i in range(1000)]
    print_table(data, ["A", "B"], "Large Table")


def test_print_table_missing_headers():
    """
    Test print_table with headers not present in any data row.
    Should not raise an error.
    """
    from alexa_manager.utils import print_table

    data = [{"A": 1}, {"A": 2}]
    print_table(data, ["X", "Y"], "Missing Headers Table")
