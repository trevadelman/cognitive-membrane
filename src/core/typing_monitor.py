"""
Typing Monitor Implementation

This module provides detailed typing pattern monitoring and analysis, capturing
keystroke timing, burst patterns, and pause durations to help understand the
user's cognitive flow through their typing behavior.
"""

import asyncio
import sys
from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import List, Optional, Dict
import statistics

@dataclass
class KeyStroke:
    """Represents a single keystroke event."""
    key: str
    timestamp: datetime
    duration: float  # How long the key was held down

@dataclass
class TypingPattern:
    """Represents a detected typing pattern."""
    avg_speed: float  # Characters per minute
    burst_duration: float  # Duration of typing burst in seconds
    pause_duration: float  # Duration of pause after burst in seconds
    timestamp: datetime

@dataclass
class TypingBurst:
    """Represents a continuous burst of typing activity."""
    keystrokes: List[KeyStroke]
    start_time: datetime
    end_time: datetime
    chars_per_minute: float
    average_keystroke_duration: float

class TypingPatternAnalyzer:
    """Analyzes typing patterns to detect cognitive state indicators."""
    
    def __init__(self):
        """Initialize the typing pattern analyzer."""
        self.bursts: List[TypingBurst] = []
        self.pause_threshold = 2.0  # seconds between keystrokes to consider a pause
        
    def analyze_burst(self, keystrokes: List[KeyStroke]) -> Optional[TypingBurst]:
        """Analyze a sequence of keystrokes to identify typing patterns.
        
        Args:
            keystrokes: List of keystroke events to analyze
            
        Returns:
            TypingBurst if a valid burst is detected, None otherwise
        """
        if not keystrokes or len(keystrokes) < 2:
            return None
            
        start_time = keystrokes[0].timestamp
        end_time = keystrokes[-1].timestamp
        duration = (end_time - start_time).total_seconds()
        
        if duration <= 0:
            return None
            
        # Calculate typing speed
        char_count = len(keystrokes)
        chars_per_minute = (char_count / duration) * 60
        
        # Calculate average keystroke duration
        avg_duration = statistics.mean(k.duration for k in keystrokes)
        
        return TypingBurst(
            keystrokes=keystrokes,
            start_time=start_time,
            end_time=end_time,
            chars_per_minute=chars_per_minute,
            average_keystroke_duration=avg_duration
        )
        
    def is_pause_start(self, current: KeyStroke, next_key: KeyStroke) -> bool:
        """Determine if a pause starts between two keystrokes.
        
        Args:
            current: The current keystroke
            next_key: The next keystroke
            
        Returns:
            True if the time between keystrokes exceeds the pause threshold
        """
        time_between = (next_key.timestamp - current.timestamp).total_seconds()
        return time_between >= self.pause_threshold

class EnhancedTypingMonitor:
    """Enhanced typing monitor with detailed pattern analysis."""
    
    def __init__(self, sampling_rate: int = 100):
        """Initialize the enhanced typing monitor.
        
        Args:
            sampling_rate: Sampling rate in milliseconds
        """
        self.sampling_rate = sampling_rate
        self.current_burst: List[KeyStroke] = []
        self.analyzer = TypingPatternAnalyzer()
        self.bursts: List[TypingBurst] = []
        self.pause_starts: List[datetime] = []
        self.pause_ends: List[datetime] = []
        
    async def start(self) -> None:
        """Start monitoring typing activity."""
        try:
            while True:
                await self._sample_typing()
                await asyncio.sleep(self.sampling_rate / 1000)
        except Exception as e:
            print(f"Error in enhanced typing monitor: {e}")
            
    def _on_key_press(self, event) -> None:
        """Handle key press events.
        
        Args:
            event: The keyboard event to handle
        """
        self.current_key = event.key
        self.key_press_time = event.timestamp
        
    def _on_key_release(self, event) -> None:
        """Handle key release events.
        
        Args:
            event: The keyboard event to handle
        """
        if self.current_key == event.key:
            duration = (event.timestamp - self.key_press_time).total_seconds()
            keystroke = KeyStroke(
                key=event.key,
                timestamp=self.key_press_time,
                duration=duration
            )
            self._process_keystroke(keystroke)
            self.current_key = None
            self.key_press_time = None
            
    async def _sample_typing(self) -> None:
        """Sample current typing activity."""
        # Initialize keyboard monitor based on platform
        if sys.platform == 'darwin':
            from .macos_keyboard_monitor import MacOSKeyboardMonitor
            self.keyboard_monitor = MacOSKeyboardMonitor()
        else:
            raise NotImplementedError(f"Platform {sys.platform} not supported yet")
            
        # Initialize key tracking
        self.current_key = None
        self.key_press_time = None
        
        # Register keyboard event handlers
        self.keyboard_monitor.register_handler('press', self._on_key_press)
        self.keyboard_monitor.register_handler('release', self._on_key_release)
        
        # Start keyboard monitoring
        await self.keyboard_monitor.start()
        
    def _process_keystroke(self, keystroke: KeyStroke) -> None:
        """Process a new keystroke event.
        
        Args:
            keystroke: The keystroke event to process
        """
        if not self.current_burst:
            self.current_burst.append(keystroke)
            return
            
        last_keystroke = self.current_burst[-1]
        
        if self.analyzer.is_pause_start(last_keystroke, keystroke):
            # End current burst
            if burst := self.analyzer.analyze_burst(self.current_burst):
                self.bursts.append(burst)
                self.pause_starts.append(last_keystroke.timestamp)
                self.pause_ends.append(keystroke.timestamp)
            self.current_burst = [keystroke]
        else:
            self.current_burst.append(keystroke)
            
    def get_recent_patterns(self, window: timedelta = timedelta(minutes=5)) -> Dict:
        """Get typing patterns from the recent time window.
        
        Args:
            window: Time window to analyze
            
        Returns:
            Dictionary containing typing pattern metrics
        """
        cutoff = datetime.now() - window
        recent_bursts = [b for b in self.bursts if b.end_time > cutoff]
        
        if not recent_bursts:
            return {
                'average_speed': 0.0,
                'burst_count': 0,
                'average_burst_duration': 0.0,
                'average_pause_duration': 0.0
            }
            
        speeds = [b.chars_per_minute for b in recent_bursts]
        durations = [(b.end_time - b.start_time).total_seconds() 
                    for b in recent_bursts]
                    
        recent_pauses = [
            (end - start).total_seconds()
            for start, end in zip(self.pause_starts, self.pause_ends)
            if end > cutoff
        ]
        
        return {
            'average_speed': statistics.mean(speeds),
            'burst_count': len(recent_bursts),
            'average_burst_duration': statistics.mean(durations),
            'average_pause_duration': statistics.mean(recent_pauses) 
                                    if recent_pauses else 0.0
        }
