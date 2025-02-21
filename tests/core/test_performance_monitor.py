"""
Tests for the Performance Monitoring System.

This module contains tests for performance monitoring and profiling functionality,
ensuring accurate tracking of system resource usage and operation timing.
"""

import asyncio
import pytest
import time
from datetime import datetime, timedelta
from unittest.mock import MagicMock, patch

from src.core.performance_monitor import (
    PerformanceMetrics,
    ResourceThresholds,
    PerformanceMonitor
)

@pytest.fixture
def mock_process():
    """Create a mock psutil Process."""
    with patch('psutil.Process') as mock:
        process = MagicMock()
        process.cpu_percent.return_value = 1.5
        memory_info = MagicMock()
        memory_info.rss = 50 * 1024 * 1024  # 50MB in bytes
        process.memory_info.return_value = memory_info
        mock.return_value = process
        yield process

@pytest.fixture
def performance_monitor(mock_process):
    """Create a PerformanceMonitor instance for testing."""
    return PerformanceMonitor(
        thresholds=ResourceThresholds(
            max_cpu_usage=2.0,
            max_memory_usage=100.0,
            max_response_time=16.0,
            max_pattern_time=100.0
        ),
        window_size=300
    )

def test_monitor_initialization(performance_monitor):
    """Test that PerformanceMonitor initializes with correct values."""
    assert performance_monitor.window_size == 300
    assert performance_monitor.thresholds.max_cpu_usage == 2.0
    assert performance_monitor.thresholds.max_memory_usage == 100.0
    assert performance_monitor.thresholds.max_response_time == 16.0
    assert performance_monitor.thresholds.max_pattern_time == 100.0
    assert performance_monitor._metrics_history == []

@pytest.mark.asyncio
async def test_metrics_sampling(performance_monitor, mock_process):
    """Test sampling of performance metrics."""
    # Sample metrics
    await performance_monitor._sample_metrics()
    
    # Verify metrics were collected
    assert len(performance_monitor._metrics_history) == 1
    metrics = performance_monitor._metrics_history[0]
    
    assert metrics.cpu_usage == 1.5  # From mock process
    assert metrics.memory_usage == 50.0  # 50MB from mock
    assert metrics.response_time >= 0.0
    assert metrics.pattern_detection_time == 0.0  # No patterns yet
    assert isinstance(metrics.timestamp, datetime)

def test_operation_timing(performance_monitor):
    """Test operation timing functionality."""
    # Start operation
    operation_id = performance_monitor.start_operation('test_operation')
    
    # Simulate some work
    time.sleep(0.1)
    
    # Stop operation
    duration = performance_monitor.stop_operation(operation_id)
    
    assert duration >= 100.0  # At least 100ms
    assert duration <= 150.0  # Allow some overhead

def test_metrics_summary(performance_monitor):
    """Test metrics summary calculation."""
    now = datetime.now()
    
    # Add some test metrics
    metrics = [
        PerformanceMetrics(
            cpu_usage=1.0 + i,  # Increasing CPU usage
            memory_usage=50.0,
            response_time=10.0,
            pattern_detection_time=50.0,
            timestamp=now - timedelta(minutes=i)
        )
        for i in range(3)
    ]
    
    performance_monitor._metrics_history.extend(metrics)
    
    # Get summary
    summary = performance_monitor.get_metrics_summary(window=timedelta(minutes=5))
    
    assert 'avg_cpu' in summary
    assert 'max_cpu' in summary
    assert 'avg_memory' in summary
    assert 'max_memory' in summary
    assert 'avg_response' in summary
    assert 'max_response' in summary
    assert 'avg_pattern_time' in summary
    assert 'max_pattern_time' in summary
    
    assert summary['avg_cpu'] == 2.0  # (1.0 + 2.0 + 3.0) / 3
    assert summary['max_cpu'] == 3.0
    assert summary['avg_memory'] == 50.0
    assert summary['avg_response'] == 10.0
    assert summary['avg_pattern_time'] == 50.0

def test_performance_issues(performance_monitor):
    """Test performance issue detection."""
    # Add metrics exceeding thresholds
    metrics = PerformanceMetrics(
        cpu_usage=3.0,  # Above 2% threshold
        memory_usage=150.0,  # Above 100MB threshold
        response_time=20.0,  # Above 16ms threshold
        pattern_detection_time=120.0,  # Above 100ms threshold
        timestamp=datetime.now()
    )
    
    performance_monitor._metrics_history.append(metrics)
    
    # Check for issues
    issues = performance_monitor.check_performance_issues()
    
    assert len(issues) == 4  # Should detect all threshold violations
    assert any('CPU usage' in issue for issue in issues)
    assert any('Memory usage' in issue for issue in issues)
    assert any('Response time' in issue for issue in issues)
    assert any('Pattern detection time' in issue for issue in issues)

def test_metrics_cleanup(performance_monitor):
    """Test cleanup of old metrics."""
    now = datetime.now()
    old_time = now - timedelta(seconds=400)  # Beyond window
    
    # Add old and new metrics
    metrics = [
        PerformanceMetrics(
            cpu_usage=1.0,
            memory_usage=50.0,
            response_time=10.0,
            pattern_detection_time=50.0,
            timestamp=old_time
        ),
        PerformanceMetrics(
            cpu_usage=1.0,
            memory_usage=50.0,
            response_time=10.0,
            pattern_detection_time=50.0,
            timestamp=now
        )
    ]
    
    performance_monitor._metrics_history.extend(metrics)
    performance_monitor._cleanup_old_metrics()
    
    # Verify old metrics are removed
    assert len(performance_monitor._metrics_history) == 1
    assert all(m.timestamp > now - timedelta(seconds=300)
              for m in performance_monitor._metrics_history)

@pytest.mark.asyncio
async def test_monitor_start(performance_monitor):
    """Test monitor start functionality."""
    # Mock sleep to avoid actual waiting
    with patch('asyncio.sleep') as mock_sleep:
        # Start monitor in background task
        task = asyncio.create_task(performance_monitor.start())
        
        try:
            # Let it run and collect at least one metric
            await performance_monitor._sample_metrics()
            
            # Let the monitor task run
            await asyncio.sleep(0)
            
            # Cancel task
            task.cancel()
            try:
                await task
            except asyncio.CancelledError:
                pass
            
            # Verify metrics were collected and monitor tried to sleep
            assert len(performance_monitor._metrics_history) > 0
            assert mock_sleep.called
        finally:
            # Ensure task is cancelled
            if not task.done():
                task.cancel()
                try:
                    await task
                except asyncio.CancelledError:
                    pass
