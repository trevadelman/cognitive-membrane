"""
Pattern Recognition System

This module implements the core pattern recognition functionality, analyzing user
activity data to detect meaningful patterns in typing, tool usage, and focus states.
It forms the foundation for understanding user behavior and cognitive flow.
"""

import asyncio
from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Set
import statistics

from .typing_monitor import TypingPattern
from .activity_monitor import ActivityMetrics

@dataclass
class ActivityPattern:
    """Represents a detected activity pattern."""
    pattern_type: str  # 'typing', 'focus', 'tool'
    start_time: datetime
    end_time: datetime
    intensity: float  # 0.0 to 1.0
    confidence: float  # 0.0 to 1.0
    metrics: Dict[str, float]  # Pattern-specific metrics

@dataclass
class ContextChange:
    """Represents a detected context switch."""
    timestamp: datetime
    from_context: str
    to_context: str
    change_duration: float  # seconds
    confidence: float  # 0.0 to 1.0

class PatternRecognizer:
    """Analyzes activity data to detect meaningful patterns."""
    
    def __init__(self, window_size: int = 300):  # 5 minutes default
        """Initialize the pattern recognizer.
        
        Args:
            window_size: Analysis window size in seconds
        """
        self.window_size = window_size
        self.activity_patterns: List[ActivityPattern] = []
        self.context_changes: List[ContextChange] = []
        self._typing_history: List[TypingPattern] = []
        self._activity_history: List[ActivityMetrics] = []
        
    def add_typing_pattern(self, pattern: TypingPattern) -> None:
        """Add a typing pattern for analysis.
        
        Args:
            pattern: The typing pattern to analyze
        """
        self._typing_history.append(pattern)
        self._cleanup_old_data()
        self._analyze_typing_patterns()
        
    def add_activity_metrics(self, metrics: ActivityMetrics) -> None:
        """Add activity metrics for analysis.
        
        Args:
            metrics: The activity metrics to analyze
        """
        self._activity_history.append(metrics)
        self._cleanup_old_data()
        self._analyze_activity_metrics()
        
    def get_recent_patterns(self, 
                          window: timedelta = timedelta(minutes=5)
                          ) -> List[ActivityPattern]:
        """Get recently detected patterns.
        
        Args:
            window: Time window to look back
            
        Returns:
            List of activity patterns within the window
        """
        cutoff = datetime.now() - window
        return [p for p in self.activity_patterns if p.end_time > cutoff]
        
    def get_recent_context_changes(self,
                                 window: timedelta = timedelta(minutes=5)
                                 ) -> List[ContextChange]:
        """Get recently detected context changes.
        
        Args:
            window: Time window to look back
            
        Returns:
            List of context changes within the window
        """
        cutoff = datetime.now() - window
        return [c for c in self.context_changes if c.timestamp > cutoff]
        
    def _cleanup_old_data(self) -> None:
        """Remove data outside the analysis window."""
        cutoff = datetime.now() - timedelta(seconds=self.window_size)
        
        self._typing_history = [
            p for p in self._typing_history if p.timestamp > cutoff
        ]
        self._activity_history = [
            m for m in self._activity_history if m.timestamp > cutoff
        ]
        self.activity_patterns = [
            p for p in self.activity_patterns if p.end_time > cutoff
        ]
        self.context_changes = [
            c for c in self.context_changes if c.timestamp > cutoff
        ]
        
    def _analyze_typing_patterns(self) -> None:
        """Analyze typing patterns to detect activity patterns."""
        if not self._typing_history:
            return
            
        # Remove any existing typing patterns
        self.activity_patterns = [p for p in self.activity_patterns 
                                if p.pattern_type != 'typing']
            
        # Calculate typing intensity
        speeds = [p.avg_speed for p in self._typing_history]
        avg_speed = statistics.mean(speeds)
        max_speed = max(speeds)
        intensity = avg_speed / max_speed if max_speed > 0 else 0.0
        
        # Calculate pattern confidence based on consistency
        if len(speeds) > 1:
            speed_variance = statistics.variance(speeds)
            consistency = 1.0 / (1.0 + speed_variance)
        else:
            consistency = 0.5
            
        # Create single typing activity pattern
        pattern = ActivityPattern(
            pattern_type='typing',
            start_time=self._typing_history[0].timestamp,
            end_time=self._typing_history[-1].timestamp,
            intensity=intensity,
            confidence=consistency,
            metrics={
                'avg_speed': avg_speed,
                'consistency': consistency,
                'burst_count': len(self._typing_history)
            }
        )
        
        self.activity_patterns.append(pattern)
        
    def _analyze_activity_metrics(self) -> None:
        """Analyze activity metrics to detect patterns and context changes."""
        if len(self._activity_history) < 2:
            return
            
        # Look for significant changes in focus duration or tool switches
        for i in range(1, len(self._activity_history)):
            prev = self._activity_history[i-1]
            curr = self._activity_history[i]
            
            # Detect context changes
            if curr.focus_duration < prev.focus_duration:
                # Focus break detected
                context_change = ContextChange(
                    timestamp=curr.timestamp,
                    from_context='focused',
                    to_context='switching',
                    change_duration=curr.focus_duration,
                    confidence=min(1.0, curr.tool_switches / 5.0)  # More switches = higher confidence
                )
                self.context_changes.append(context_change)
            
            # Detect tool usage patterns
            if curr.tool_switches > prev.tool_switches:
                # Tool usage burst detected
                pattern = ActivityPattern(
                    pattern_type='tool',
                    start_time=prev.timestamp,
                    end_time=curr.timestamp,
                    intensity=min(1.0, curr.tool_switches / 10.0),
                    confidence=0.8,  # Tool switches are reliable indicators
                    metrics={
                        'switch_count': curr.tool_switches,
                        'typing_speed': curr.typing_speed
                    }
                )
                self.activity_patterns.append(pattern)
