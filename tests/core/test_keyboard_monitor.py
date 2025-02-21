"""
Tests for the Keyboard Monitor.

This module contains tests for the keyboard event monitoring and processing
functionality, using mocked system events to validate behavior.
"""

import asyncio
import pytest
from datetime import datetime, timedelta
from typing import Set
from src.core.keyboard_monitor import (
    KeyboardEvent,
    KeyboardMonitor,
    KeyboardEventProcessor
)

@pytest.fixture
def keyboard_monitor():
    """Fixture to create a KeyboardMonitor instance."""
    return KeyboardMonitor()

@pytest.fixture
def event_processor():
    """Fixture to create a KeyboardEventProcessor instance."""
    return KeyboardEventProcessor()

def create_keyboard_event(
    key: str,
    event_type: str,
    modifiers: Set[str] = None
) -> KeyboardEvent:
    """Helper function to create keyboard events for testing.
    
    Args:
        key: The key involved in the event
        event_type: Type of event ('press' or 'release')
        modifiers: Set of modifier keys active during the event
        
    Returns:
        KeyboardEvent object
    """
    return KeyboardEvent(
        key=key,
        event_type=event_type,
        timestamp=datetime.now(),
        modifiers=modifiers or set()
    )

def test_keyboard_event_creation():
    """Test that KeyboardEvent objects can be created with valid values."""
    timestamp = datetime.now()
    event = KeyboardEvent(
        key='a',
        event_type='press',
        timestamp=timestamp,
        modifiers={'shift'}
    )
    
    assert event.key == 'a'
    assert event.event_type == 'press'
    assert event.timestamp == timestamp
    assert event.modifiers == {'shift'}

def test_monitor_initialization(keyboard_monitor):
    """Test that KeyboardMonitor initializes with correct default values."""
    assert not keyboard_monitor._is_running
    assert keyboard_monitor._pressed_keys == set()
    assert keyboard_monitor._key_press_times == {}
    assert keyboard_monitor.handlers == {}

def test_handler_registration(keyboard_monitor):
    """Test handler registration and unregistration."""
    def test_handler(event):
        pass
    
    # Register handler
    keyboard_monitor.register_handler('press', test_handler)
    assert keyboard_monitor.handlers['press'] == test_handler
    
    # Unregister handler
    keyboard_monitor.unregister_handler('press')
    assert 'press' not in keyboard_monitor.handlers

def test_key_press_handling(keyboard_monitor):
    """Test that key press events are handled correctly."""
    pressed_keys = []
    
    def test_handler(event):
        pressed_keys.append(event.key)
    
    keyboard_monitor.register_handler('press', test_handler)
    timestamp = datetime.now()
    
    # Simulate key press
    keyboard_monitor._handle_key_press('a', timestamp)
    
    assert 'a' in keyboard_monitor._pressed_keys
    assert keyboard_monitor._key_press_times['a'] == timestamp
    assert pressed_keys == ['a']

def test_key_release_handling(keyboard_monitor):
    """Test that key release events are handled correctly."""
    released_keys = []
    
    def test_handler(event):
        released_keys.append(event.key)
    
    keyboard_monitor.register_handler('release', test_handler)
    
    # Simulate key press and release
    press_time = datetime.now()
    keyboard_monitor._handle_key_press('a', press_time)
    
    release_time = press_time + timedelta(seconds=0.1)
    keyboard_monitor._handle_key_release('a', release_time)
    
    assert 'a' not in keyboard_monitor._pressed_keys
    assert 'a' not in keyboard_monitor._key_press_times
    assert released_keys == ['a']

def test_modifier_key_tracking(keyboard_monitor):
    """Test that modifier keys are correctly tracked."""
    events = []
    
    def test_handler(event):
        events.append(event)
    
    keyboard_monitor.register_handler('press', test_handler)
    
    # Press shift, then 'a'
    keyboard_monitor._handle_key_press('shift', datetime.now())
    keyboard_monitor._handle_key_press('a', datetime.now())
    
    assert len(events) == 2
    assert 'shift' in events[1].modifiers

@pytest.mark.asyncio
async def test_monitor_start_stop(keyboard_monitor):
    """Test that the monitor can start and stop gracefully."""
    # Start monitor
    await keyboard_monitor.start()
    assert keyboard_monitor._is_running
    
    # Stop monitor
    await keyboard_monitor.stop()
    assert not keyboard_monitor._is_running

@pytest.mark.asyncio
async def test_event_processor_start_stop(event_processor):
    """Test that the event processor can start and stop gracefully."""
    # Start processor
    await event_processor.start()
    assert event_processor.monitor._is_running
    
    # Stop processor
    await event_processor.stop()
    assert not event_processor.monitor._is_running

def test_key_duration_calculation(keyboard_monitor):
    """Test that key hold durations are calculated correctly."""
    durations = []
    
    def duration_handler(key, duration):
        durations.append((key, duration))
    
    keyboard_monitor.register_handler('duration', duration_handler)
    
    # Simulate key press and release with 0.1s duration
    press_time = datetime.now()
    keyboard_monitor._handle_key_press('a', press_time)
    
    release_time = press_time + timedelta(seconds=0.1)
    keyboard_monitor._handle_key_release('a', release_time)
    
    assert len(durations) == 1
    assert durations[0][0] == 'a'
    assert 0.09 <= durations[0][1] <= 0.11  # Allow small timing variations
