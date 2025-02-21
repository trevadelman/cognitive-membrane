"""
Tests for the macOS Keyboard Monitor.

This module contains tests for the macOS-specific keyboard monitoring functionality,
using mocked Quartz framework calls to simulate keyboard events.
"""

import asyncio
import pytest
from datetime import datetime
from unittest.mock import MagicMock, patch
from typing import Set

from src.core.macos_keyboard_monitor import (
    MacOSKeyboardMonitor,
    MODIFIER_MAP
)

@pytest.fixture
def mock_quartz():
    """Fixture to mock Quartz framework calls."""
    with patch('src.core.macos_keyboard_monitor.CGEventTapCreate') as mock_create, \
         patch('src.core.macos_keyboard_monitor.CGEventTapEnable') as mock_enable, \
         patch('src.core.macos_keyboard_monitor.CFMachPortCreateRunLoopSource') as mock_source, \
         patch('src.core.macos_keyboard_monitor.CFRunLoopAddSource') as mock_add_source, \
         patch('src.core.macos_keyboard_monitor.CFRunLoopGetCurrent') as mock_get_loop, \
         patch('src.core.macos_keyboard_monitor.CFRunLoopRun') as mock_run, \
         patch('src.core.macos_keyboard_monitor.CFRunLoopStop') as mock_stop:
        
        # Set up mock event tap
        mock_tap = MagicMock()
        mock_create.return_value = mock_tap
        
        # Set up mock run loop source
        mock_loop_source = MagicMock()
        mock_source.return_value = mock_loop_source
        
        yield {
            'create_tap': mock_create,
            'enable_tap': mock_enable,
            'create_source': mock_source,
            'add_source': mock_add_source,
            'get_loop': mock_get_loop,
            'run_loop': mock_run,
            'stop_loop': mock_stop,
            'event_tap': mock_tap,
            'loop_source': mock_loop_source
        }

@pytest.fixture
def keyboard_monitor():
    """Fixture to create a MacOSKeyboardMonitor instance."""
    return MacOSKeyboardMonitor()

@pytest.fixture(autouse=True)
def mock_quartz_functions():
    """Mock Quartz functions globally for all tests."""
    with patch('src.core.macos_keyboard_monitor.CGEventGetIntegerValueField') as mock_get_field, \
         patch('src.core.macos_keyboard_monitor.CGEventGetFlags') as mock_get_flags:
        
        def get_field_side_effect(event, field_type):
            return getattr(event, '_keycode', 0)
            
        def get_flags_side_effect(event):
            return getattr(event, '_flags', 0)
            
        mock_get_field.side_effect = get_field_side_effect
        mock_get_flags.side_effect = get_flags_side_effect
        yield

def create_mock_event(keycode: int, flags: int = 0):
    """Helper function to create mock keyboard events."""
    event = MagicMock()
    event._keycode = keycode
    event._flags = flags
    return event

@pytest.mark.asyncio
async def test_monitor_initialization(keyboard_monitor):
    """Test that the monitor initializes with correct default values."""
    assert not keyboard_monitor._is_running
    assert keyboard_monitor._event_tap is None
    assert keyboard_monitor._run_loop_source is None
    assert keyboard_monitor._run_loop_thread is None

@pytest.mark.asyncio
async def test_monitor_start(keyboard_monitor, mock_quartz):
    """Test that the monitor starts correctly."""
    await keyboard_monitor.start()
    
    # Verify event tap creation
    mock_quartz['create_tap'].assert_called_once()
    mock_quartz['enable_tap'].assert_called_once_with(
        mock_quartz['event_tap'],
        True
    )
    
    # Verify run loop setup
    mock_quartz['create_source'].assert_called_once()
    mock_quartz['add_source'].assert_called_once()
    
    assert keyboard_monitor._is_running
    
    # Clean up
    await keyboard_monitor.stop()

@pytest.mark.asyncio
async def test_monitor_stop(keyboard_monitor, mock_quartz):
    """Test that the monitor stops correctly."""
    # Mock the run loop and thread
    mock_loop = MagicMock()
    mock_thread = MagicMock()
    mock_thread.is_alive.return_value = True
    
    # Set up mocks
    mock_quartz['get_loop'].return_value = mock_loop
    
    # Start the monitor
    with patch('threading.Thread') as mock_thread_class:
        mock_thread_class.return_value = mock_thread
        await keyboard_monitor.start()
        assert keyboard_monitor._is_running
        assert keyboard_monitor._current_loop == mock_loop
        assert keyboard_monitor._run_loop_thread == mock_thread
        
        # Stop the monitor
        await keyboard_monitor.stop()
        
        # Verify the event tap was disabled
        mock_quartz['enable_tap'].assert_called_with(
            mock_quartz['event_tap'],
            False
        )
        
        # Verify the run loop was stopped
        mock_quartz['stop_loop'].assert_called_once_with(mock_loop)
        mock_thread.join.assert_called_once_with(timeout=1.0)
    
    # Verify cleanup
    assert not keyboard_monitor._is_running
    assert keyboard_monitor._event_tap is None
    assert keyboard_monitor._run_loop_source is None
    assert keyboard_monitor._run_loop_thread is None
    
    assert not keyboard_monitor._is_running
    assert keyboard_monitor._event_tap is None
    assert keyboard_monitor._run_loop_source is None
    assert keyboard_monitor._run_loop_thread is None

def test_keycode_to_char(keyboard_monitor):
    """Test keycode to character conversion."""
    from src.core.macos_keyboard_monitor import kCGEventFlagMaskShift
    
    # Test basic letter conversion
    assert keyboard_monitor._keycode_to_char(0, 0) == 'a'  # 'a' keycode
    assert keyboard_monitor._keycode_to_char(45, 0) == 'n'  # 'n' keycode
    
    # Test letter case with shift
    assert keyboard_monitor._keycode_to_char(0, kCGEventFlagMaskShift) == 'A'
    assert keyboard_monitor._keycode_to_char(45, kCGEventFlagMaskShift) == 'N'
    
    # Test numbers and symbols
    assert keyboard_monitor._keycode_to_char(18, 0) == '1'
    assert keyboard_monitor._keycode_to_char(29, 0) == '0'
    assert keyboard_monitor._keycode_to_char(41, 0) == ';'
    
    # Test shifted symbols
    assert keyboard_monitor._keycode_to_char(18, kCGEventFlagMaskShift) == '!'  # Shift + 1
    assert keyboard_monitor._keycode_to_char(41, kCGEventFlagMaskShift) == ':'  # Shift + ;
    
    # Test special keys
    assert keyboard_monitor._keycode_to_char(36, 0) == 'Return'
    assert keyboard_monitor._keycode_to_char(49, 0) == 'Space'
    assert keyboard_monitor._keycode_to_char(53, 0) == 'Escape'
    
    # Test function keys
    assert keyboard_monitor._keycode_to_char(122, 0) == 'F1'
    assert keyboard_monitor._keycode_to_char(120, 0) == 'F2'
    
    # Test arrow keys
    assert keyboard_monitor._keycode_to_char(123, 0) == 'Left'
    assert keyboard_monitor._keycode_to_char(124, 0) == 'Right'
    assert keyboard_monitor._keycode_to_char(125, 0) == 'Down'
    assert keyboard_monitor._keycode_to_char(126, 0) == 'Up'
    
    # Test out of range keycode
    assert keyboard_monitor._keycode_to_char(999, 0) is None

def test_event_callback_key_press(keyboard_monitor):
    """Test handling of key press events."""
    from src.core.macos_keyboard_monitor import kCGEventKeyDown
    
    # Create mock event
    event = create_mock_event(0)  # 'a' keycode
    
    # Create handler to capture events
    pressed_keys = []
    keyboard_monitor.register_handler('press', lambda e: pressed_keys.append(e.key))
    
    # Simulate key press
    result = keyboard_monitor._create_event_callback(None, kCGEventKeyDown, event, None)
    
    assert result == event  # Event should propagate
    assert pressed_keys == ['a']

def test_event_callback_with_modifiers(keyboard_monitor):
    """Test handling of events with modifier keys."""
    from src.core.macos_keyboard_monitor import (
        kCGEventKeyDown,
        kCGEventFlagMaskShift,
        kCGEventFlagMaskControl
    )
    
    # Create mock event with modifiers
    event = create_mock_event(0, kCGEventFlagMaskShift | kCGEventFlagMaskControl)
    
    # Create handler to capture events
    events = []
    keyboard_monitor.register_handler('press', lambda e: events.append(e))
    
    # Simulate key press
    keyboard_monitor._create_event_callback(None, kCGEventKeyDown, event, None)
    
    assert len(events) == 1
    assert events[0].key == 'A'  # Shift makes it uppercase
    assert 'shift' in events[0].modifiers
    assert 'ctrl' in events[0].modifiers

def test_event_callback_error_handling(keyboard_monitor):
    """Test that event callback handles errors gracefully."""
    from src.core.macos_keyboard_monitor import kCGEventKeyDown
    
    # Create mock event that will cause an error
    event = MagicMock()
    event.getIntegerValueField.side_effect = Exception("Test error")
    
    # Event should still propagate despite error
    result = keyboard_monitor._create_event_callback(None, kCGEventKeyDown, event, None)
    assert result == event

@pytest.mark.asyncio
async def test_monitor_restart(keyboard_monitor, mock_quartz):
    """Test that the monitor can be stopped and restarted."""
    # First start
    await keyboard_monitor.start()
    assert keyboard_monitor._is_running
    
    # Stop
    await keyboard_monitor.stop()
    assert not keyboard_monitor._is_running
    
    # Restart
    await keyboard_monitor.start()
    assert keyboard_monitor._is_running
    
    # Clean up
    await keyboard_monitor.stop()
