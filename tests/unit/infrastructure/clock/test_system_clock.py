"""Tests for SystemClock."""

import time

import pytest

from src.infrastructure.clock.system_clock import SystemClock


@pytest.mark.unit
def test_now_ms_returns_current_time_in_milliseconds():
    """Test now_ms returns current time in epoch milliseconds."""
    clock = SystemClock()

    # Get time before and after
    before_ms = int(time.time() * 1000)
    result = clock.now_ms()
    after_ms = int(time.time() * 1000)

    # Result should be between before and after (within a few milliseconds)
    assert before_ms <= result <= after_ms


@pytest.mark.unit
def test_now_ms_returns_integer():
    """Test now_ms returns an integer."""
    clock = SystemClock()

    result = clock.now_ms()

    assert isinstance(result, int)


@pytest.mark.unit
def test_now_ms_increases_over_time():
    """Test now_ms returns increasing values over time."""
    clock = SystemClock()

    first = clock.now_ms()
    time.sleep(0.01)  # Sleep 10ms
    second = clock.now_ms()

    assert second > first


@pytest.mark.unit
def test_now_ms_returns_reasonable_value():
    """Test now_ms returns a reasonable epoch milliseconds value."""
    clock = SystemClock()

    result = clock.now_ms()

    # Should be a reasonable value (after 2020, before 2100)
    # 2020-01-01 = 1577836800000 ms
    # 2100-01-01 = 4102444800000 ms
    assert 1577836800000 < result < 4102444800000
