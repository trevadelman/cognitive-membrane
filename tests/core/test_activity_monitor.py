"""
Tests for the Core Activity Monitor.

This module contains tests for the basic functionality of the activity monitoring
system, ensuring that the core infrastructure works as expected.
"""

import asyncio
import pytest
from datetime import datetime, timedelta
from src.core.activity_monitor import (
    CoreActivityMonitor,
    ActivityMetrics,
    TypingPattern,
    TypingMonitor,
    FocusMonitor,
    ToolUsageMonitor
)

@pytest.fixture
def activity_monitor():
    """Fixture to create a CoreActivityMonitor instance."""
    return CoreActivityMonitor()

@pytest.fixture
def typing_monitor():
    """Fixture to create a TypingMonitor instance."""
    return TypingMonitor()

@pytest.fixture
def focus_monitor():
    """Fixture to create a FocusMonitor instance."""
    return FocusMonitor()

@pytest.fixture
def tool_monitor():
    """Fixture to create a ToolUsageMonitor instance."""
    return ToolUsageMonitor()

def test_activity_metrics_creation():
    """Test that ActivityMetrics can be created with valid values."""
    metrics = ActivityMetrics(
        typing_speed=60.0,
        focus_duration=300.0,
        tool_switches=5,
        timestamp=datetime.now()
    )
    
    assert metrics.typing_speed == 60.0
    assert metrics.focus_duration == 300.0
    assert metrics.tool_switches == 5
    assert isinstance(metrics.timestamp, datetime)

def test_typing_pattern_creation():
    """Test that TypingPattern can be created with valid values."""
    pattern = TypingPattern(
        avg_speed=60.0,
        burst_duration=5.0,
        pause_duration=1.0,
        timestamp=datetime.now()
    )
    
    assert pattern.avg_speed == 60.0
    assert pattern.burst_duration == 5.0
    assert pattern.pause_duration == 1.0
    assert isinstance(pattern.timestamp, datetime)

@pytest.mark.asyncio
async def test_typing_monitor_initialization(typing_monitor):
    """Test that TypingMonitor initializes with correct default values."""
    assert typing_monitor.sampling_rate == 100
    assert typing_monitor.typing_history == []
    assert typing_monitor._current_burst == []
    assert typing_monitor._last_keystroke is None

@pytest.mark.asyncio
async def test_focus_monitor_initialization(focus_monitor):
    """Test that FocusMonitor initializes with correct default values."""
    assert focus_monitor.window_size == 5
    assert focus_monitor.current_focus is None
    assert focus_monitor.focus_start is None
    assert focus_monitor.focus_history == []

@pytest.mark.asyncio
async def test_tool_monitor_initialization(tool_monitor):
    """Test that ToolUsageMonitor initializes with correct default values."""
    assert tool_monitor.tool_history == []
    assert tool_monitor.active_tool is None

@pytest.mark.asyncio
async def test_core_monitor_initialization(activity_monitor):
    """Test that CoreActivityMonitor initializes all subsystems."""
    assert isinstance(activity_monitor.typing_monitor, TypingMonitor)
    assert isinstance(activity_monitor.focus_monitor, FocusMonitor)
    assert isinstance(activity_monitor.tool_monitor, ToolUsageMonitor)

@pytest.mark.asyncio
async def test_get_current_metrics(activity_monitor):
    """Test that get_current_metrics returns valid ActivityMetrics."""
    metrics = activity_monitor.get_current_metrics()
    
    assert isinstance(metrics, ActivityMetrics)
    assert metrics.typing_speed == 0.0  # Default value for now
    assert metrics.focus_duration == 0.0  # Default value for now
    assert metrics.tool_switches == 0  # Default value for now
    assert isinstance(metrics.timestamp, datetime)

@pytest.mark.asyncio
async def test_monitor_start_stop(activity_monitor):
    """Test that the monitor can start and stop gracefully."""
    # Create a task for the monitor
    monitor_task = asyncio.create_task(activity_monitor.start())
    
    # Let it run for a brief moment
    await asyncio.sleep(0.1)
    
    # Cancel the task (simulating shutdown)
    monitor_task.cancel()
    
    try:
        await monitor_task
    except asyncio.CancelledError:
        pass  # Expected behavior
    
    # Verify the monitor stopped gracefully
    assert True  # If we got here without errors, the test passed

@pytest.mark.asyncio
async def test_focus_duration_calculation(focus_monitor):
    """Test that focus duration is calculated correctly."""
    # Simulate focus start
    focus_monitor.focus_start = datetime.now() - timedelta(seconds=10)
    focus_monitor.current_focus = "test_window"
    
    duration = focus_monitor.get_focus_duration()
    assert duration >= 10.0  # Should be approximately 10 seconds
    assert duration < 11.0  # Allow for small timing variations
