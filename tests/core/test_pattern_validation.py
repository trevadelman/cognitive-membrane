"""
Tests for the Pattern Validation System.

This module contains tests for pattern validation mechanisms, ensuring they
correctly validate activity patterns and context changes.
"""

import pytest
from datetime import datetime, timedelta
from typing import List

from src.core.pattern_validation import (
    ValidationResult,
    PatternValidator
)
from src.core.pattern_recognition import (
    ActivityPattern,
    ContextChange
)

def create_activity_pattern(
    pattern_type: str,
    start_time: datetime,
    duration: float,
    intensity: float = 0.8,
    confidence: float = 0.7,
    metrics: dict = None
) -> ActivityPattern:
    """Create an activity pattern for testing.
    
    Args:
        pattern_type: Type of pattern ('typing', 'tool', etc.)
        start_time: Pattern start time
        duration: Pattern duration in seconds
        intensity: Pattern intensity (0.0 to 1.0)
        confidence: Pattern confidence (0.0 to 1.0)
        metrics: Pattern-specific metrics
        
    Returns:
        ActivityPattern instance
    """
    end_time = start_time + timedelta(seconds=duration)
    return ActivityPattern(
        pattern_type=pattern_type,
        start_time=start_time,
        end_time=end_time,
        intensity=intensity,
        confidence=confidence,
        metrics=metrics or {
            'consistency': 0.8,
            'burst_count': 3,
            'avg_speed': 60.0
        }
    )

def create_context_change(
    timestamp: datetime,
    duration: float,
    confidence: float = 0.7,
    from_context: str = 'focused',
    to_context: str = 'switching'
) -> ContextChange:
    """Create a context change for testing.
    
    Args:
        timestamp: Change timestamp
        duration: Change duration in seconds
        confidence: Change confidence (0.0 to 1.0)
        from_context: Original context
        to_context: New context
        
    Returns:
        ContextChange instance
    """
    return ContextChange(
        timestamp=timestamp,
        from_context=from_context,
        to_context=to_context,
        change_duration=duration,
        confidence=confidence
    )

@pytest.fixture
def pattern_validator():
    """Create a PatternValidator instance for testing."""
    return PatternValidator(
        min_confidence=0.5,
        min_duration=1.0,
        max_variance=100.0
    )

def test_validator_initialization(pattern_validator):
    """Test that PatternValidator initializes with correct values."""
    assert pattern_validator.min_confidence == 0.5
    assert pattern_validator.min_duration == 1.0
    assert pattern_validator.max_variance == 100.0
    assert pattern_validator._pattern_history == []
    assert pattern_validator._context_history == []

def test_validate_activity_pattern_basic(pattern_validator):
    """Test basic activity pattern validation."""
    now = datetime.now()
    
    # Create valid pattern
    pattern = create_activity_pattern(
        pattern_type='typing',
        start_time=now - timedelta(seconds=10),
        duration=5.0
    )
    
    result = pattern_validator.validate_activity_pattern(pattern)
    assert result.is_valid
    assert result.confidence >= pattern_validator.min_confidence
    assert not result.anomalies
    
    # Create invalid pattern (too short)
    short_pattern = create_activity_pattern(
        pattern_type='typing',
        start_time=now,
        duration=0.5  # Below min_duration
    )
    
    result = pattern_validator.validate_activity_pattern(short_pattern)
    assert not result.is_valid
    assert 'Pattern duration too short' in result.anomalies

def test_validate_activity_pattern_history(pattern_validator):
    """Test activity pattern validation against history."""
    now = datetime.now()
    
    # Add some historical patterns
    for i in range(3):
        pattern = create_activity_pattern(
            pattern_type='typing',
            start_time=now - timedelta(minutes=i+1),
            duration=5.0,
            metrics={
                'consistency': 0.8,
                'burst_count': 3,
                'avg_speed': 60.0 + i  # Slight variation
            }
        )
        pattern_validator.validate_activity_pattern(pattern)
    
    # Test similar pattern
    similar_pattern = create_activity_pattern(
        pattern_type='typing',
        start_time=now,
        duration=5.0,
        metrics={
            'consistency': 0.75,
            'burst_count': 3,
            'avg_speed': 62.0
        }
    )
    
    result = pattern_validator.validate_activity_pattern(similar_pattern)
    assert result.is_valid
    assert result.confidence > 0.7  # Should get history boost
    assert not result.anomalies
    assert 'avg_avg_speed' in result.metrics
    assert 'var_avg_speed' in result.metrics
    
    # Test anomalous pattern
    anomalous_pattern = create_activity_pattern(
        pattern_type='typing',
        start_time=now,
        duration=5.0,
        metrics={
            'consistency': 0.2,  # Much lower consistency
            'burst_count': 3,
            'avg_speed': 120.0  # Much higher speed
        }
    )
    
    result = pattern_validator.validate_activity_pattern(anomalous_pattern)
    assert not result.is_valid
    assert len(result.anomalies) > 0

def test_validate_context_change(pattern_validator):
    """Test context change validation."""
    now = datetime.now()
    
    # Test valid context change
    change = create_context_change(
        timestamp=now,
        duration=2.0,
        confidence=0.8
    )
    
    result = pattern_validator.validate_context_change(change)
    assert result.is_valid
    assert result.confidence >= pattern_validator.min_confidence
    assert not result.anomalies
    
    # Test rapid context switching
    for i in range(6):  # More than 5 changes per minute
        change = create_context_change(
            timestamp=now - timedelta(seconds=i*10),
            duration=2.0
        )
        result = pattern_validator.validate_context_change(change)
        
    assert not result.is_valid
    assert 'Too many context changes' in result.anomalies

def test_pattern_cleanup(pattern_validator):
    """Test cleanup of old patterns."""
    now = datetime.now()
    old_time = now - timedelta(minutes=40)  # Beyond 30 minute window
    
    # Add old and new patterns
    old_pattern = create_activity_pattern(
        pattern_type='typing',
        start_time=old_time,
        duration=5.0
    )
    new_pattern = create_activity_pattern(
        pattern_type='typing',
        start_time=now,
        duration=5.0
    )
    
    pattern_validator.validate_activity_pattern(old_pattern)
    pattern_validator.validate_activity_pattern(new_pattern)
    
    # Add old and new context changes
    old_change = create_context_change(
        timestamp=old_time,
        duration=2.0
    )
    new_change = create_context_change(
        timestamp=now,
        duration=2.0
    )
    
    pattern_validator.validate_context_change(old_change)
    pattern_validator.validate_context_change(new_change)
    
    # Verify old data is cleaned up
    assert len(pattern_validator._pattern_history) == 1
    assert len(pattern_validator._context_history) == 1
    assert all(p.end_time > now - timedelta(minutes=30) 
              for p in pattern_validator._pattern_history)
    assert all(c.timestamp > now - timedelta(minutes=30)
              for c in pattern_validator._context_history)

def test_similar_pattern_detection(pattern_validator):
    """Test detection of similar patterns."""
    now = datetime.now()
    base_pattern = create_activity_pattern(
        pattern_type='typing',
        start_time=now,
        duration=5.0,
        intensity=0.8
    )
    
    # Add patterns with varying similarity
    patterns = [
        create_activity_pattern(  # Similar
            pattern_type='typing',
            start_time=now - timedelta(minutes=1),
            duration=5.0,
            intensity=0.75
        ),
        create_activity_pattern(  # Different type
            pattern_type='tool',
            start_time=now - timedelta(minutes=2),
            duration=5.0,
            intensity=0.8
        ),
        create_activity_pattern(  # Too different intensity
            pattern_type='typing',
            start_time=now - timedelta(minutes=3),
            duration=5.0,
            intensity=0.3
        )
    ]
    
    for pattern in patterns:
        pattern_validator.validate_activity_pattern(pattern)
        
    similar = pattern_validator._find_similar_patterns(base_pattern)
    assert len(similar) == 1  # Only the first pattern should be similar
    assert similar[0].pattern_type == 'typing'
    assert abs(similar[0].intensity - base_pattern.intensity) < 0.2
