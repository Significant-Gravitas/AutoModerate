"""
In-memory error tracking for system health monitoring
"""
import time
from collections import deque
from threading import Lock
from typing import Dict, List


class ErrorTracker:
    """Track recent errors for monitoring and debugging"""

    # Shared error tracking across all instances
    _recent_errors = deque(maxlen=100)  # Keep last 100 errors
    _error_counts = {
        'database': 0,
        'processing': 0,
        'api': 0,
        'moderation': 0,
        'other': 0
    }
    _lock = Lock()

    @classmethod
    def track_error(cls, error_type: str, message: str, content_id: str = None, details: Dict = None):
        """
        Track an error occurrence

        Args:
            error_type: Type of error (database, processing, api, moderation, other)
            message: Error message
            content_id: Optional content ID associated with error
            details: Optional additional details
        """
        with cls._lock:
            error_entry = {
                'timestamp': time.time(),
                'type': error_type,
                'message': message,
                'content_id': content_id,
                'details': details or {}
            }
            cls._recent_errors.append(error_entry)

            # Increment error type counter
            if error_type in cls._error_counts:
                cls._error_counts[error_type] += 1
            else:
                cls._error_counts['other'] += 1

    @classmethod
    def get_recent_errors(cls, limit: int = 50) -> List[Dict]:
        """Get recent errors with optional limit"""
        with cls._lock:
            # Convert deque to list and get last N items
            errors = list(cls._recent_errors)[-limit:]
            # Add human-readable timestamps
            for error in errors:
                seconds_ago = int(time.time() - error['timestamp'])
                if seconds_ago < 60:
                    error['time_ago'] = f"{seconds_ago}s ago"
                elif seconds_ago < 3600:
                    error['time_ago'] = f"{seconds_ago // 60}m ago"
                else:
                    error['time_ago'] = f"{seconds_ago // 3600}h ago"
            return errors

    @classmethod
    def get_error_counts(cls) -> Dict[str, int]:
        """Get error counts by type"""
        with cls._lock:
            return cls._error_counts.copy()

    @classmethod
    def get_error_stats(cls) -> Dict:
        """Get comprehensive error statistics"""
        with cls._lock:
            total_errors = sum(cls._error_counts.values())
            recent_count = len(cls._recent_errors)

            # Count errors in last 5 minutes
            five_min_ago = time.time() - 300
            recent_5min = sum(1 for e in cls._recent_errors if e['timestamp'] > five_min_ago)

            return {
                'total_errors': total_errors,
                'recent_errors': recent_count,
                'errors_last_5min': recent_5min,
                'error_counts': cls._error_counts.copy()
            }

    @classmethod
    def clear_old_errors(cls, max_age_seconds: int = 3600):
        """Clear errors older than specified age (default 1 hour)"""
        with cls._lock:
            cutoff_time = time.time() - max_age_seconds
            # Keep only recent errors
            while cls._recent_errors and cls._recent_errors[0]['timestamp'] < cutoff_time:
                cls._recent_errors.popleft()


# Create singleton instance
error_tracker = ErrorTracker()
