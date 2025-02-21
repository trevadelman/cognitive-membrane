"""
Pattern Validation System

This module implements validation mechanisms for detected patterns, ensuring
their accuracy and reliability through statistical analysis and confidence scoring.
"""

import statistics
from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Set, Tuple

from .pattern_recognition import ActivityPattern, ContextChange
from .typing_monitor import TypingPattern

@dataclass
class ValidationResult:
    """Results of pattern validation."""
    is_valid: bool
    confidence: float  # 0.0 to 1.0
    metrics: Dict[str, float]
    anomalies: List[str]

class PatternValidator:
    """Validates detected patterns for accuracy and reliability."""
    
    def __init__(self, 
                 min_confidence: float = 0.5,
                 min_duration: float = 1.0,  # seconds
                 max_variance: float = 100.0):
        """Initialize the pattern validator.
        
        Args:
            min_confidence: Minimum confidence threshold for valid patterns
            min_duration: Minimum duration threshold for valid patterns
            max_variance: Maximum allowed variance in pattern metrics
        """
        self.min_confidence = min_confidence
        self.min_duration = min_duration
        self.max_variance = max_variance
        self._pattern_history: List[ActivityPattern] = []
        self._context_history: List[ContextChange] = []
        
    def validate_activity_pattern(self, pattern: ActivityPattern) -> ValidationResult:
        """Validate an activity pattern.
        
        Args:
            pattern: The activity pattern to validate
            
        Returns:
            ValidationResult containing validation metrics
        """
        # Store pattern for historical analysis
        self._pattern_history.append(pattern)
        self._cleanup_old_patterns()
        
        # Basic validation checks
        duration = (pattern.end_time - pattern.start_time).total_seconds()
        if duration < self.min_duration:
            return ValidationResult(
                is_valid=False,
                confidence=0.0,
                metrics={'duration': duration},
                anomalies=['Pattern duration too short']
            )
            
        if pattern.confidence < self.min_confidence:
            return ValidationResult(
                is_valid=False,
                confidence=pattern.confidence,
                metrics={'confidence': pattern.confidence},
                anomalies=['Pattern confidence too low']
            )
            
        # Validate against historical patterns
        similar_patterns = self._find_similar_patterns(pattern)
        if not similar_patterns:
            # First pattern of its type, validate based on internal metrics
            return self._validate_new_pattern(pattern)
            
        # Compare with historical patterns
        return self._validate_against_history(pattern, similar_patterns)
        
    def validate_context_change(self, change: ContextChange) -> ValidationResult:
        """Validate a context change detection.
        
        Args:
            change: The context change to validate
            
        Returns:
            ValidationResult containing validation metrics
        """
        # Store change for historical analysis
        self._context_history.append(change)
        self._cleanup_old_patterns()
        
        # Basic validation checks
        if change.confidence < self.min_confidence:
            return ValidationResult(
                is_valid=False,
                confidence=change.confidence,
                metrics={'confidence': change.confidence},
                anomalies=['Context change confidence too low']
            )
            
        # Validate change duration
        if change.change_duration < self.min_duration:
            return ValidationResult(
                is_valid=False,
                confidence=0.0,
                metrics={'duration': change.change_duration},
                anomalies=['Context change duration too short']
            )
            
        # Check for rapid context switching
        recent_changes = self._get_recent_changes(window=timedelta(minutes=1))
        if len(recent_changes) > 5:  # More than 5 changes per minute is suspicious
            return ValidationResult(
                is_valid=False,
                confidence=0.0,
                metrics={'change_frequency': len(recent_changes)},
                anomalies=['Too many context changes']
            )
            
        return ValidationResult(
            is_valid=True,
            confidence=change.confidence,
            metrics={
                'duration': change.change_duration,
                'change_frequency': len(recent_changes)
            },
            anomalies=[]
        )
        
    def _cleanup_old_patterns(self) -> None:
        """Remove patterns older than the analysis window."""
        cutoff = datetime.now() - timedelta(minutes=30)  # 30 minute history
        
        self._pattern_history = [
            p for p in self._pattern_history 
            if p.end_time > cutoff
        ]
        self._context_history = [
            c for c in self._context_history 
            if c.timestamp > cutoff
        ]
        
    def _find_similar_patterns(self, 
                             pattern: ActivityPattern
                             ) -> List[ActivityPattern]:
        """Find historically similar patterns.
        
        Args:
            pattern: Pattern to find similar matches for
            
        Returns:
            List of similar patterns from history
        """
        return [
            p for p in self._pattern_history
            if p.pattern_type == pattern.pattern_type
            and abs(p.intensity - pattern.intensity) < 0.2
            and p != pattern  # Don't include the pattern itself
        ]
        
    def _validate_new_pattern(self, pattern: ActivityPattern) -> ValidationResult:
        """Validate a pattern with no historical context.
        
        Args:
            pattern: Pattern to validate
            
        Returns:
            ValidationResult based on internal metrics
        """
        # Check for internal consistency
        metrics = pattern.metrics
        anomalies = []
        
        if 'consistency' in metrics:
            if metrics['consistency'] < 0.3:  # Low internal consistency
                anomalies.append('Low internal consistency')
                
        if 'burst_count' in metrics:
            if metrics['burst_count'] < 2:  # Need multiple bursts
                anomalies.append('Insufficient data points')
                
        # Calculate confidence based on metrics and anomalies
        base_confidence = pattern.confidence
        confidence_penalty = len(anomalies) * 0.2
        final_confidence = max(0.0, base_confidence - confidence_penalty)
        
        return ValidationResult(
            is_valid=final_confidence >= self.min_confidence,
            confidence=final_confidence,
            metrics=metrics,
            anomalies=anomalies
        )
        
    def _validate_against_history(self,
                                pattern: ActivityPattern,
                                similar_patterns: List[ActivityPattern]
                                ) -> ValidationResult:
        """Validate a pattern against historical patterns.
        
        Args:
            pattern: Pattern to validate
            similar_patterns: List of similar historical patterns
            
        Returns:
            ValidationResult based on historical comparison
        """
        anomalies = []
        
        # Compare pattern metrics with historical averages
        historical_metrics = {}
        for metric_name in pattern.metrics:
            historical_values = [
                p.metrics[metric_name] for p in similar_patterns
                if metric_name in p.metrics
            ]
            if historical_values:
                avg = statistics.mean(historical_values)
                var = statistics.variance(historical_values) if len(historical_values) > 1 else 0
                
                # Check if current value is within expected range
                current = pattern.metrics[metric_name]
                if var > 0 and abs(current - avg) / var > self.max_variance:
                    anomalies.append(f'Unusual {metric_name} value')
                    
                historical_metrics[f'avg_{metric_name}'] = avg
                historical_metrics[f'var_{metric_name}'] = var
                
        # Calculate confidence based on similarity to history
        base_confidence = pattern.confidence
        confidence_boost = len(similar_patterns) * 0.1  # More history = more confidence
        confidence_penalty = len(anomalies) * 0.2
        final_confidence = min(1.0, max(0.0, 
                                      base_confidence + confidence_boost - confidence_penalty))
        
        return ValidationResult(
            is_valid=final_confidence >= self.min_confidence and not anomalies,
            confidence=final_confidence,
            metrics={**pattern.metrics, **historical_metrics},
            anomalies=anomalies
        )
        
    def _get_recent_changes(self,
                          window: timedelta = timedelta(minutes=5)
                          ) -> List[ContextChange]:
        """Get context changes within the recent window.
        
        Args:
            window: Time window to look back
            
        Returns:
            List of recent context changes
        """
        cutoff = datetime.now() - window
        return [c for c in self._context_history if c.timestamp > cutoff]
