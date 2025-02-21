"""
Tests for the Enhanced Typing Monitor.

This module contains tests for the typing pattern analysis functionality,
ensuring accurate detection of typing bursts, pauses, and pattern metrics.
"""

import asyncio
import pytest
from datetime import datetime, timedelta
from src.core.typing_monitor import (
    KeyStroke,
    TypingBurst,
    TypingPatternAnalyzer,
    EnhancedTypingMonitor
)

@pytest.fixture
def typing_analyzer():
    """Fixture to create a TypingPatternAnalyzer instance."""
    return TypingPatternAnalyzer()

@pytest.fixture
def typing_monitor():
    """Fixture to create an EnhancedTypingMonitor instance."""
    return EnhancedTypingMonitor()

def create_test_keystrokes(
    base_time: datetime,
    count: int,
    interval: float = 0.1,
    duration: float = 0.05
) -> list[KeyStroke]:
    """Helper function to create test keystroke sequences.
    
    Args:
        base_time: Starting timestamp for the sequence
        count: Number of keystrokes to generate
        interval: Time between keystrokes in seconds
        duration: Duration of each keystroke in seconds
        
    Returns:
        List of KeyStroke objects
    """
    keystrokes = []
    for i in range(count):
        timestamp = base_time + timedelta(seconds=i * interval)
        keystrokes.append(KeyStroke(
            key=chr(97 + (i % 26)),  # a-z characters
            timestamp=timestamp,
            duration=duration
        ))
    return keystrokes

def test_keystroke_creation():
    """Test that KeyStroke objects can be created with valid values."""
    timestamp = datetime.now()
    keystroke = KeyStroke(
        key='a',
        timestamp=timestamp,
        duration=0.05
    )
    
    assert keystroke.key == 'a'
    assert keystroke.timestamp == timestamp
    assert keystroke.duration == 0.05

def test_typing_burst_creation():
    """Test that TypingBurst objects can be created with valid values."""
    start_time = datetime.now()
    keystrokes = create_test_keystrokes(start_time, 5)
    end_time = keystrokes[-1].timestamp
    
    burst = TypingBurst(
        keystrokes=keystrokes,
        start_time=start_time,
        end_time=end_time,
        chars_per_minute=60.0,
        average_keystroke_duration=0.05
    )
    
    assert len(burst.keystrokes) == 5
    assert burst.start_time == start_time
    assert burst.end_time == end_time
    assert burst.chars_per_minute == 60.0
    assert burst.average_keystroke_duration == 0.05

def test_burst_analysis(typing_analyzer):
    """Test that typing bursts are correctly analyzed."""
    base_time = datetime.now()
    keystrokes = create_test_keystrokes(base_time, 10, interval=0.2)
    
    burst = typing_analyzer.analyze_burst(keystrokes)
    
    assert burst is not None
    assert len(burst.keystrokes) == 10
    assert burst.start_time == base_time
    assert burst.end_time == keystrokes[-1].timestamp
    # 10 chars / 1.8 seconds * 60 = 333.33... chars per minute
    assert 330 <= burst.chars_per_minute <= 334
    assert burst.average_keystroke_duration == 0.05

def test_pause_detection(typing_analyzer):
    """Test that pauses between keystrokes are correctly detected."""
    base_time = datetime.now()
    
    # Create two keystrokes with a pause between them
    current = KeyStroke('a', base_time, 0.05)
    next_key = KeyStroke('b', base_time + timedelta(seconds=3), 0.05)
    
    assert typing_analyzer.is_pause_start(current, next_key)
    
    # Test with keystrokes close together (no pause)
    next_key = KeyStroke('b', base_time + timedelta(seconds=0.2), 0.05)
    assert not typing_analyzer.is_pause_start(current, next_key)

def test_empty_burst_analysis(typing_analyzer):
    """Test handling of empty or invalid keystroke sequences."""
    assert typing_analyzer.analyze_burst([]) is None
    assert typing_analyzer.analyze_burst([KeyStroke('a', datetime.now(), 0.05)]) is None

def test_recent_patterns(typing_monitor):
    """Test calculation of recent typing pattern metrics."""
    base_time = datetime.now() - timedelta(minutes=1)
    
    # Create and process a sequence of keystrokes
    keystrokes = create_test_keystrokes(base_time, 20, interval=0.2)
    for keystroke in keystrokes:
        typing_monitor._process_keystroke(keystroke)
    
    # Add a pause
    pause_keystroke = KeyStroke(
        'x',
        base_time + timedelta(seconds=10),
        0.05
    )
    typing_monitor._process_keystroke(pause_keystroke)
    
    patterns = typing_monitor.get_recent_patterns(window=timedelta(minutes=5))
    
    assert patterns['burst_count'] > 0
    assert patterns['average_speed'] > 0
    assert patterns['average_burst_duration'] > 0
    assert patterns['average_pause_duration'] >= 0

def test_empty_recent_patterns(typing_monitor):
    """Test pattern calculation with no recent typing activity."""
    patterns = typing_monitor.get_recent_patterns()
    
    assert patterns['average_speed'] == 0.0
    assert patterns['burst_count'] == 0
    assert patterns['average_burst_duration'] == 0.0
    assert patterns['average_pause_duration'] == 0.0

@pytest.mark.asyncio
async def test_monitor_initialization(typing_monitor):
    """Test that the monitor initializes with correct default values."""
    assert typing_monitor.sampling_rate == 100
    assert typing_monitor.current_burst == []
    assert isinstance(typing_monitor.analyzer, TypingPatternAnalyzer)
    assert typing_monitor.bursts == []
    assert typing_monitor.pause_starts == []
    assert typing_monitor.pause_ends == []

@pytest.mark.asyncio
async def test_monitor_start_stop(typing_monitor):
    """Test that the monitor can start and stop gracefully."""
    # Create a task for the monitor
    monitor_task = asyncio.create_task(typing_monitor.start())
    
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
