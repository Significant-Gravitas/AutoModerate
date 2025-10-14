import hashlib
import time
from threading import RLock

from flask import current_app


class ResultCache:
    """Handles caching of moderation results to improve performance with memory leak protection"""

    # Shared cache across all instances with better memory management
    _shared_cache = {}
    _shared_cache_ttl = 3600  # 1 hour
    _current_request_stores = 0  # Track stores per request
    _cache_lock = RLock()  # Thread-safe operations
    _max_cache_size = 500  # Reduced from 1000 for high-volume deployments
    _cleanup_threshold = 400  # Start cleanup earlier
    _last_cleanup_time = 0
    _cleanup_interval = 180  # Cleanup every 3 minutes (more frequent)

    def __init__(self, cache_ttl=3600):  # 1 hour default
        self._cache_ttl = cache_ttl
        # Use class-level shared cache instead of instance cache
        ResultCache._shared_cache_ttl = cache_ttl

    def generate_cache_key(self, content, custom_prompt=None):
        """Generate a cache key based on content hash and prompt for better performance"""
        # Use content hash for large content to avoid memory issues
        if len(content) > 1000:
            content_hash = hashlib.md5(content.encode(
                'utf-8'), usedforsecurity=False).hexdigest()
            combined = f"{content_hash}_{len(content)}"
        else:
            combined = content

        if custom_prompt:
            prompt_hash = hashlib.md5(custom_prompt.encode(
                'utf-8'), usedforsecurity=False).hexdigest()[:8]
            combined = f"{combined}|{prompt_hash}"
        else:
            combined = f"{combined}|enhanced_default"

        return hashlib.md5(combined.encode('utf-8'), usedforsecurity=False).hexdigest()

    def get_cached_result(self, cache_key):
        """Get cached result if it exists and is not expired (thread-safe)"""
        with ResultCache._cache_lock:
            # Perform periodic cleanup
            self._periodic_cleanup()

            if cache_key in ResultCache._shared_cache:
                cached_data = ResultCache._shared_cache[cache_key]
                if time.time() - cached_data['timestamp'] < ResultCache._shared_cache_ttl:
                    # Cache hit - only log occasionally to reduce noise
                    if len(ResultCache._shared_cache) <= 5:
                        current_app.logger.info("Cache HIT")
                    return cached_data['result']
                else:
                    # Remove expired cache entry immediately
                    try:
                        del ResultCache._shared_cache[cache_key]
                        if current_app.logger.level <= 10:
                            current_app.logger.info(
                                f"Cache EXPIRED for key: {cache_key[:8]}...")
                    except KeyError:
                        pass  # Already removed by another thread
            return None

    def cache_result(self, cache_key, result):
        """Cache the result with timestamp (thread-safe with memory leak prevention)"""
        with ResultCache._cache_lock:
            # Check if cache is at capacity before adding
            if len(ResultCache._shared_cache) >= ResultCache._max_cache_size:
                self._aggressive_cleanup()

            # Only cache if we have space or successfully cleaned up
            if len(ResultCache._shared_cache) < ResultCache._max_cache_size:
                ResultCache._shared_cache[cache_key] = {
                    'result': result,
                    'timestamp': time.time()
                }

                # Track stores for this request
                ResultCache._current_request_stores += 1
            else:
                # Cache is full, log warning
                current_app.logger.warning("Cache full, dropping new entry to prevent memory leak")

            # Perform cleanup if we've reached the threshold
            if len(ResultCache._shared_cache) >= ResultCache._cleanup_threshold:
                self._cleanup_expired_entries()

    def get_request_cache_summary(self):
        """Get summary of cache operations for current request"""
        stores = ResultCache._current_request_stores
        total = len(ResultCache._shared_cache)
        ResultCache._current_request_stores = 0  # Reset for next request
        return {'stores': stores, 'total': total}

    def invalidate_cache(self, cache_key=None):
        """Invalidate specific cache entry or all entries (thread-safe)"""
        with ResultCache._cache_lock:
            if cache_key:
                ResultCache._shared_cache.pop(cache_key, None)
            else:
                ResultCache._shared_cache.clear()
                current_app.logger.info("Cache cleared completely")

    def get_cache_stats(self):
        """Get cache statistics for monitoring"""
        current_time = time.time()
        expired_count = sum(1 for data in ResultCache._shared_cache.values()
                            if current_time - data['timestamp'] >= ResultCache._shared_cache_ttl)

        return {
            'total_entries': len(ResultCache._shared_cache),
            'expired_entries': expired_count,
            'valid_entries': len(ResultCache._shared_cache) - expired_count,
            'cache_size_mb': self._estimate_cache_size(),
            'oldest_entry_age': self._get_oldest_entry_age()
        }

    def _periodic_cleanup(self):
        """Perform periodic cleanup to prevent memory leaks"""
        current_time = time.time()
        if current_time - ResultCache._last_cleanup_time > ResultCache._cleanup_interval:
            self._cleanup_expired_entries()
            ResultCache._last_cleanup_time = current_time

    def _cleanup_expired_entries(self):
        """Remove expired entries from cache"""
        current_time = time.time()
        expired_keys = []

        for key, data in list(ResultCache._shared_cache.items()):
            if current_time - data['timestamp'] >= ResultCache._shared_cache_ttl:
                expired_keys.append(key)

        # Remove expired entries
        for key in expired_keys:
            ResultCache._shared_cache.pop(key, None)

        if expired_keys:
            current_app.logger.info(f"Cleaned up {len(expired_keys)} expired cache entries")

    def _aggressive_cleanup(self):
        """Perform aggressive cleanup when cache is full"""
        current_time = time.time()
        entries_to_remove = []

        # Remove entries older than 50% of TTL
        for key, data in list(ResultCache._shared_cache.items()):
            if current_time - data['timestamp'] >= ResultCache._shared_cache_ttl * 0.5:
                entries_to_remove.append((key, data['timestamp']))

        # If not enough old entries, remove oldest 25%
        if len(entries_to_remove) < len(ResultCache._shared_cache) * 0.25:
            all_entries = [(key, data['timestamp']) for key, data in ResultCache._shared_cache.items()]
            all_entries.sort(key=lambda x: x[1])  # Sort by timestamp
            entries_to_remove.extend(all_entries[:len(ResultCache._shared_cache) // 4])

        # Remove the entries
        removed_count = 0
        for key, _ in entries_to_remove[:500]:  # Limit to prevent blocking
            if ResultCache._shared_cache.pop(key, None) is not None:
                removed_count += 1

        if removed_count > 0:
            current_app.logger.info(f"Aggressive cleanup: removed {removed_count} cache entries")

    def _estimate_cache_size(self):
        """Rough estimate of cache size in MB"""
        if not ResultCache._shared_cache:
            return 0.0

        # Sample a few entries to estimate average size
        sample_keys = list(ResultCache._shared_cache.keys())[:min(10, len(ResultCache._shared_cache))]
        total_size = 0

        for key in sample_keys:
            try:
                # Rough estimate: key + result data
                entry_size = len(str(key)) + len(str(ResultCache._shared_cache[key]['result']))
                total_size += entry_size
            except (KeyError, TypeError):
                continue  # Skip corrupted entries

        if sample_keys and total_size > 0:
            avg_size = total_size / len(sample_keys)
            total_estimated_size = avg_size * len(ResultCache._shared_cache)
            return total_estimated_size / (1024 * 1024)  # Convert to MB

        return 0.0

    def _get_oldest_entry_age(self):
        """Get age of oldest cache entry in seconds"""
        if not ResultCache._shared_cache:
            return 0

        current_time = time.time()
        oldest_timestamp = min(data['timestamp']
                               for data in ResultCache._shared_cache.values())
        return current_time - oldest_timestamp
