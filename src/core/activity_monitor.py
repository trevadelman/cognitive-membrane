"""
Core Activity Monitor for the Cognitive Membrane.

This module implements the foundational activity monitoring system that tracks user
interactions and work patterns. It provides the raw data needed for higher-level
pattern recognition and cognitive field analysis.
"""

import asyncio
import statistics
import sys
from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import Dict, List, Optional

from .typing_monitor import EnhancedTypingMonitor

@dataclass
class ActivityMetrics:
    """Container for current activity metrics."""
    typing_speed: float  # Characters per minute
    focus_duration: float  # Seconds in current context
    tool_switches: int  # Number of tool switches in last minute
    timestamp: datetime

@dataclass
class TypingPattern:
    """Represents a detected typing pattern."""
    avg_speed: float  # Characters per minute
    burst_duration: float  # Duration of typing burst in seconds
    pause_duration: float  # Duration of pause after burst in seconds
    timestamp: datetime

class TypingMonitor:
    """Monitors and analyzes typing patterns."""
    
    def __init__(self, sampling_rate: int = 100):
        """Initialize the typing monitor.
        
        Args:
            sampling_rate: Sampling rate in milliseconds
        """
        self.sampling_rate = sampling_rate
        self.typing_history: List[TypingPattern] = []
        self._current_burst: List[str] = []
        self._last_keystroke: Optional[datetime] = None
        
    async def start(self) -> None:
        """Start monitoring typing activity."""
        try:
            while True:
                await self._sample_typing()
                await asyncio.sleep(self.sampling_rate / 1000)  # Convert to seconds
        except Exception as e:
            # Log error and attempt recovery
            print(f"Error in typing monitor: {e}")
            # In a real implementation, we would use proper logging
            # and error recovery mechanisms
            
    async def _sample_typing(self) -> None:
        """Sample current typing activity."""
        # Initialize and start keyboard monitoring
        self.typing_monitor = EnhancedTypingMonitor()
        await self.typing_monitor.start()
    
    def calculate_metrics(self, window: timedelta = timedelta(minutes=5)) -> TypingPattern:
        """Calculate current typing metrics.
        
        Args:
            window: Time window to analyze
            
        Returns:
            TypingPattern containing the calculated metrics
        """
        if not self.typing_history:
            return TypingPattern(
                avg_speed=0.0,
                burst_duration=0.0,
                pause_duration=0.0,
                timestamp=datetime.now()
            )
            
        recent_patterns = [p for p in self.typing_history 
                         if p.timestamp > datetime.now() - window]
        
        if not recent_patterns:
            return TypingPattern(
                avg_speed=0.0,
                burst_duration=0.0,
                pause_duration=0.0,
                timestamp=datetime.now()
            )
            
        avg_speed = statistics.mean(p.avg_speed for p in recent_patterns)
        avg_burst = statistics.mean(p.burst_duration for p in recent_patterns)
        avg_pause = statistics.mean(p.pause_duration for p in recent_patterns)
        
        return TypingPattern(
            avg_speed=avg_speed,
            burst_duration=avg_burst,
            pause_duration=avg_pause,
            timestamp=datetime.now()
        )

class FocusMonitor:
    """Monitors user focus and context switches."""
    
    def __init__(self, window_size: int = 5):
        """Initialize the focus monitor.
        
        Args:
            window_size: Size of the focus window in seconds
        """
        self.window_size = window_size
        self.current_focus: Optional[str] = None
        self.focus_start: Optional[datetime] = None
        self.focus_history: List[Dict] = []
        
    async def start(self) -> None:
        """Start monitoring focus state."""
        try:
            while True:
                await self._sample_focus()
                await asyncio.sleep(0.1)  # 100ms sampling rate
        except Exception as e:
            print(f"Error in focus monitor: {e}")
            
    async def _sample_focus(self) -> None:
        """Sample current focus state."""
        # Get the currently focused window/application
        if sys.platform == 'darwin':
            from .macos_keyboard_monitor import MacOSKeyboardMonitor
            # For now, we'll just return a basic structure
            # In the future, this will use macOS-specific APIs to get window info
            return {
                'application': 'Unknown',
                'window_title': 'Unknown',
                'duration': 0.0
            }
        else:
            raise NotImplementedError(f"Platform {sys.platform} not supported yet")
        # This will track which window/document has focus
        pass
    
    def get_focus_duration(self) -> float:
        """Get the duration of current focus in seconds."""
        if not self.focus_start:
            return 0.0
        return (datetime.now() - self.focus_start).total_seconds()

class ToolUsageMonitor:
    """Monitors tool usage patterns."""
    
    def __init__(self):
        """Initialize the tool usage monitor."""
        self.tool_history: List[Dict] = []
        self.active_tool: Optional[str] = None
        self.typing_monitor: Optional[EnhancedTypingMonitor] = None
        
    async def start(self) -> None:
        """Start monitoring tool usage."""
        try:
            # Initialize and start typing monitor
            self.typing_monitor = EnhancedTypingMonitor()
            await self.typing_monitor.start()
            
            # Start tool usage monitoring
            while True:
                await self._sample_tool_usage()
                await asyncio.sleep(0.1)  # 100ms sampling rate
        except Exception as e:
            print(f"Error in tool monitor: {e}")
            
    async def _sample_tool_usage(self) -> Dict:
        """Sample current tool usage."""
        # Get tool usage metrics from the typing monitor
        patterns = self.typing_monitor.get_recent_patterns(window=timedelta(minutes=5))
        
        # For now, we'll return basic metrics
        # In the future, this will track actual tool usage
        return {
            'tool_switches': len(patterns['pause_starts']),
            'average_tool_duration': patterns['average_burst_duration'],
            'total_active_time': sum(b.end_time - b.start_time 
                                   for b in self.typing_monitor.bursts)
        }
    
    def get_tool_switches(self) -> int:
        """Get the number of tool switches in the last minute."""
        if not self.typing_monitor:
            return 0
            
        # Get tool switch metrics from the typing monitor
        patterns = self.typing_monitor.get_recent_patterns(window=timedelta(minutes=1))
        
        # For now, we'll use typing pauses as a proxy for tool switches
        # In the future, this will track actual tool switches
        return len(patterns['pause_starts'])

class CoreActivityMonitor:
    """Core activity monitoring system.
    
    This class coordinates the various monitoring subsystems and provides
    a unified interface for accessing activity metrics.
    """
    
    def __init__(self):
        """Initialize the core activity monitor."""
        self.typing_monitor = TypingMonitor()
        self.focus_monitor = FocusMonitor()
        self.tool_monitor = ToolUsageMonitor()
        
    async def start(self) -> None:
        """Start all monitoring systems."""
        try:
            # Start all monitors concurrently
            await asyncio.gather(
                self.typing_monitor.start(),
                self.focus_monitor.start(),
                self.tool_monitor.start()
            )
        except Exception as e:
            print(f"Error starting activity monitor: {e}")
            
    def get_current_metrics(self) -> ActivityMetrics:
        """Get current activity metrics."""
        typing_pattern = self.typing_monitor.calculate_metrics()
        
        return ActivityMetrics(
            typing_speed=typing_pattern.avg_speed,
            focus_duration=self.focus_monitor.get_focus_duration(),
            tool_switches=self.tool_monitor.get_tool_switches(),
            timestamp=datetime.now()
        )

if __name__ == "__main__":
    # Simple test code
    async def main():
        monitor = CoreActivityMonitor()
        await monitor.start()
    
    asyncio.run(main())
