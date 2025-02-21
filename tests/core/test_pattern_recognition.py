"""
Tests for the Pattern Recognition System.

This module contains tests for pattern detection, context change recognition,
and activity analysis functionality.
"""

import pytest
from datetime import datetime, timedelta
from typing import List

from src.core.pattern_recognition import (
    ActivityPattern,
    ContextChange,
    PatternRecognizer
)
from src.core.typing_monitor import TypingPattern
from src.core.activity_monitor import ActivityMetrics

def create_typing_pattern(
    avg_speed: float,
    timestamp: datetime,
    burst_duration: float = 1.0,
    pause_duration: float = 0.5
) -> TypingPattern:
    """Create a typing pattern for testing.
    
    Args:
        avg_speed: Average typing speed
        timestamp: Pattern timestamp
        burst_duration: Duration of typing burst
        pause_duration: Duration of pause after burst
        
    Returns:
        TypingPattern instance
    """
    return TypingPattern(
        avg_speed=avg_speed,
        burst_duration=burst_duration,
        pause_duration=pause_duration,
        timestamp=timestamp
    )

def create_activity_metrics(
    typing_speed: float,
    focus_duration: float,
    tool_switches: int,
    timestamp: datetime
) -> ActivityMetrics:
    """Create activity metrics for testing.
    
    Args:
        typing_speed: Current typing speed
        focus_duration: Duration of current focus
        tool_switches: Number of tool switches
        timestamp: Metrics timestamp
        
    Returns:
        ActivityMetrics instance
    """
    return ActivityMetrics(
        typing_speed=typing_speed,
        focus_duration=focus_duration,
        tool_switches=tool_switches,
        timestamp=timestamp
    )

@pytest.fixture
def pattern_recognizer():
    """Create a PatternRecognizer instance for testing."""
    return PatternRecognizer(window_size=300)  # 5 minutes

def test_pattern_recognizer_initialization(pattern_recognizer):
    """Test that PatternRecognizer initializes with correct default values."""
    assert pattern_recognizer.window_size == 300
    assert pattern_recognizer.activity_patterns == []
    assert pattern_recognizer.context_changes == []
    assert pattern_recognizer._typing_history == []
    assert pattern_recognizer._activity_history == []

def test_typing_pattern_analysis(pattern_recognizer):
    """Test analysis of typing patterns."""
    now = datetime.now()
    
    # Add some typing patterns
    patterns = [
        create_typing_pattern(60.0, now - timedelta(seconds=10)),
        create_typing_pattern(65.0, now - timedelta(seconds=8)),
        create_typing_pattern(55.0, now - timedelta(seconds=6))
    ]
    
    for pattern in patterns:
        pattern_recognizer.add_typing_pattern(pattern)
        
    # Get recent patterns
    recent = pattern_recognizer.get_recent_patterns()
    assert len(recent) == 1  # Should combine into one activity pattern
    
    pattern = recent[0]
    assert pattern.pattern_type == 'typing'
    assert pattern.start_time == patterns[0].timestamp
    assert pattern.end_time == patterns[-1].timestamp
    assert 0.0 <= pattern.intensity <= 1.0
    assert 0.0 <= pattern.confidence <= 1.0
    assert 'avg_speed' in pattern.metrics
    assert 'consistency' in pattern.metrics
    assert 'burst_count' in pattern.metrics
    assert pattern.metrics['burst_count'] == 3

def test_context_change_detection(pattern_recognizer):
    """Test detection of context changes."""
    now = datetime.now()
    
    # Add activity metrics showing focus change
    metrics = [
        create_activity_metrics(60.0, 300.0, 1, now - timedelta(seconds=10)),
        create_activity_metrics(30.0, 60.0, 3, now - timedelta(seconds=5)),  # Focus break
        create_activity_metrics(45.0, 30.0, 5, now)  # More tool switching
    ]
    
    for metric in metrics:
        pattern_recognizer.add_activity_metrics(metric)
        
    # Get recent context changes
    changes = pattern_recognizer.get_recent_context_changes()
    assert len(changes) > 0
    
    change = changes[0]
    assert change.from_context == 'focused'
    assert change.to_context == 'switching'
    assert change.change_duration == 60.0
    assert 0.0 <= change.confidence <= 1.0

def test_tool_usage_pattern_detection(pattern_recognizer):
    """Test detection of tool usage patterns."""
    now = datetime.now()
    
    # Add activity metrics showing increased tool usage
    metrics = [
        create_activity_metrics(60.0, 300.0, 1, now - timedelta(seconds=10)),
        create_activity_metrics(55.0, 280.0, 4, now - timedelta(seconds=5)),
        create_activity_metrics(50.0, 260.0, 7, now)
    ]
    
    for metric in metrics:
        pattern_recognizer.add_activity_metrics(metric)
        
    # Get recent patterns
    patterns = [p for p in pattern_recognizer.get_recent_patterns()
               if p.pattern_type == 'tool']
    assert len(patterns) > 0
    
    pattern = patterns[0]
    assert pattern.pattern_type == 'tool'
    assert pattern.start_time >= metrics[0].timestamp
    assert pattern.end_time <= metrics[-1].timestamp
    assert 0.0 <= pattern.intensity <= 1.0
    assert pattern.confidence == 0.8  # Tool patterns have fixed confidence
    assert 'switch_count' in pattern.metrics
    assert 'typing_speed' in pattern.metrics

def test_data_cleanup(pattern_recognizer):
    """Test cleanup of old data."""
    now = datetime.now()
    old_time = now - timedelta(seconds=400)  # Outside window
    
    # Add old and new typing patterns
    old_pattern = create_typing_pattern(60.0, old_time)
    new_pattern = create_typing_pattern(65.0, now)
    pattern_recognizer.add_typing_pattern(old_pattern)
    pattern_recognizer.add_typing_pattern(new_pattern)
    
    # Add old and new activity metrics
    old_metrics = create_activity_metrics(60.0, 300.0, 1, old_time)
    new_metrics = create_activity_metrics(65.0, 300.0, 2, now)
    pattern_recognizer.add_activity_metrics(old_metrics)
    pattern_recognizer.add_activity_metrics(new_metrics)
    
    # Verify old data is cleaned up
    assert all(p.timestamp > now - timedelta(seconds=300) 
              for p in pattern_recognizer._typing_history)
    assert all(m.timestamp > now - timedelta(seconds=300)
              for m in pattern_recognizer._activity_history)
    assert all(p.end_time > now - timedelta(seconds=300)
              for p in pattern_recognizer.activity_patterns)
    assert all(c.timestamp > now - timedelta(seconds=300)
              for c in pattern_recognizer.context_changes)

def test_empty_data_handling(pattern_recognizer):
    """Test handling of empty data."""
    # Get patterns with no data
    patterns = pattern_recognizer.get_recent_patterns()
    assert patterns == []
    
    # Get context changes with no data
    changes = pattern_recognizer.get_recent_context_changes()
    assert changes == []
    
    # Add single data points
    now = datetime.now()
    pattern_recognizer.add_typing_pattern(
        create_typing_pattern(60.0, now)
    )
    pattern_recognizer.add_activity_metrics(
        create_activity_metrics(60.0, 300.0, 1, now)
    )
    
    # Verify no false patterns from single points
    assert len(pattern_recognizer.get_recent_patterns()) == 1
    assert len(pattern_recognizer.get_recent_context_changes()) == 0
