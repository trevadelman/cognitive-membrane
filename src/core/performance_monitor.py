"""
Performance Monitoring System

This module implements performance monitoring and profiling functionality to ensure
the system maintains its efficiency targets while operating in the background.
"""

import asyncio
import psutil
import time
from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple
import statistics

@dataclass
class PerformanceMetrics:
    """System performance metrics."""
    cpu_usage: float  # Percentage (0-100)
    memory_usage: float  # MB
    response_time: float  # ms
    pattern_detection_time: float  # ms
    timestamp: datetime

@dataclass
class ResourceThresholds:
    """Resource usage thresholds."""
    max_cpu_usage: float = 2.0  # 2% CPU limit
    max_memory_usage: float = 100.0  # 100MB memory limit
    max_response_time: float = 16.0  # 16ms response time limit
    max_pattern_time: float = 100.0  # 100ms pattern detection limit

class PerformanceMonitor:
    """Monitors and analyzes system performance metrics."""
    
    def __init__(self, 
                 thresholds: ResourceThresholds = None,
                 window_size: int = 300):  # 5 minutes default
        """Initialize the performance monitor.
        
        Args:
            thresholds: Resource usage thresholds
            window_size: Analysis window size in seconds
        """
        self.thresholds = thresholds or ResourceThresholds()
        self.window_size = window_size
        self._metrics_history: List[PerformanceMetrics] = []
        self._process = psutil.Process()
        self._start_time = time.time()
        self._last_sample = time.time()
        self._operation_starts = {}
        self._recent_operations = {}
        
    async def start(self) -> None:
        """Start performance monitoring."""
        try:
            while True:
                await self._sample_metrics()
                await asyncio.sleep(1)  # Sample every second
        except Exception as e:
            print(f"Error in performance monitor: {e}")
            
    def start_operation(self, operation_name: str) -> int:
        """Start timing an operation.
        
        Args:
            operation_name: Name of operation to time
            
        Returns:
            Operation ID for stopping the timer
        """
        operation_id = hash(f"{operation_name}_{time.time()}")
        self._operation_starts[operation_id] = time.time()
        return operation_id
        
    def stop_operation(self, operation_id: int) -> float:
        """Stop timing an operation and get duration.
        
        Args:
            operation_id: Operation ID from start_operation
            
        Returns:
            Operation duration in milliseconds
        """
        if operation_id not in self._operation_starts:
            return 0.0
            
        start_time = self._operation_starts.pop(operation_id)
        return (time.time() - start_time) * 1000  # Convert to ms
        
    def get_current_metrics(self) -> PerformanceMetrics:
        """Get current performance metrics.
        
        Returns:
            Current PerformanceMetrics
        """
        if not self._metrics_history:
            return PerformanceMetrics(
                cpu_usage=0.0,
                memory_usage=0.0,
                response_time=0.0,
                pattern_detection_time=0.0,
                timestamp=datetime.now()
            )
            
        return self._metrics_history[-1]
        
    def get_metrics_summary(self, 
                          window: timedelta = timedelta(minutes=5)
                          ) -> Dict[str, float]:
        """Get summary statistics for recent metrics.
        
        Args:
            window: Time window to analyze
            
        Returns:
            Dictionary of metric summaries
        """
        cutoff = datetime.now() - window
        recent_metrics = [m for m in self._metrics_history 
                        if m.timestamp > cutoff]
        
        if not recent_metrics:
            return {
                'avg_cpu': 0.0,
                'max_cpu': 0.0,
                'avg_memory': 0.0,
                'max_memory': 0.0,
                'avg_response': 0.0,
                'max_response': 0.0,
                'avg_pattern_time': 0.0,
                'max_pattern_time': 0.0
            }
            
        cpu_values = [m.cpu_usage for m in recent_metrics]
        memory_values = [m.memory_usage for m in recent_metrics]
        response_values = [m.response_time for m in recent_metrics]
        pattern_values = [m.pattern_detection_time for m in recent_metrics]
        
        return {
            'avg_cpu': statistics.mean(cpu_values),
            'max_cpu': max(cpu_values),
            'avg_memory': statistics.mean(memory_values),
            'max_memory': max(memory_values),
            'avg_response': statistics.mean(response_values),
            'max_response': max(response_values),
            'avg_pattern_time': statistics.mean(pattern_values),
            'max_pattern_time': max(pattern_values)
        }
        
    def check_performance_issues(self) -> List[str]:
        """Check for performance issues.
        
        Returns:
            List of performance issue descriptions
        """
        issues = []
        metrics = self.get_current_metrics()
        
        if metrics.cpu_usage > self.thresholds.max_cpu_usage:
            issues.append(
                f"CPU usage ({metrics.cpu_usage:.1f}%) exceeds threshold "
                f"({self.thresholds.max_cpu_usage:.1f}%)"
            )
            
        if metrics.memory_usage > self.thresholds.max_memory_usage:
            issues.append(
                f"Memory usage ({metrics.memory_usage:.1f}MB) exceeds threshold "
                f"({self.thresholds.max_memory_usage:.1f}MB)"
            )
            
        if metrics.response_time > self.thresholds.max_response_time:
            issues.append(
                f"Response time ({metrics.response_time:.1f}ms) exceeds threshold "
                f"({self.thresholds.max_response_time:.1f}ms)"
            )
            
        if metrics.pattern_detection_time > self.thresholds.max_pattern_time:
            issues.append(
                f"Pattern detection time ({metrics.pattern_detection_time:.1f}ms) "
                f"exceeds threshold ({self.thresholds.max_pattern_time:.1f}ms)"
            )
            
        return issues
        
    async def _sample_metrics(self) -> None:
        """Sample current performance metrics."""
        try:
            # Get CPU and memory usage
            cpu_percent = self._process.cpu_percent()
            memory_info = self._process.memory_info()
            memory_mb = memory_info.rss / 1024 / 1024
            
            # Calculate response time (time since last sample)
            now = time.time()
            response_time = (now - self._last_sample) * 1000 if hasattr(self, '_last_sample') else 0
            self._last_sample = now
            
            # Get pattern detection time from recent operations
            pattern_times = [
                duration for op_id, duration in self._recent_operations.items()
                if 'pattern' in str(op_id).lower()
            ]
            pattern_time = statistics.mean(pattern_times) if pattern_times else 0
            
            # Create metrics
            metrics = PerformanceMetrics(
                cpu_usage=cpu_percent,
                memory_usage=memory_mb,
                response_time=response_time,
                pattern_detection_time=pattern_time,
                timestamp=datetime.now()
            )
            
            # Store metrics
            self._metrics_history.append(metrics)
            self._cleanup_old_metrics()
            
        except Exception as e:
            print(f"Error sampling metrics: {e}")
            
    def _cleanup_old_metrics(self) -> None:
        """Remove metrics outside the analysis window."""
        cutoff = datetime.now() - timedelta(seconds=self.window_size)
        self._metrics_history = [
            m for m in self._metrics_history 
            if m.timestamp > cutoff
        ]
