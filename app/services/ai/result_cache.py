import hashlib
import time

from flask import current_app


class ResultCache:
    """Handles caching of moderation results to improve performance"""

    # Shared cache across all instances
    _shared_cache = {}
    _shared_cache_ttl = 3600  # 1 hour default
    _current_request_stores = 0  # Track stores per request

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
        """Get cached result if it exists and is not expired"""
        if cache_key in ResultCache._shared_cache:
            cached_data = ResultCache._shared_cache[cache_key]
            if time.time() - cached_data['timestamp'] < ResultCache._shared_cache_ttl:
                # Cache hit - only log occasionally to reduce noise
                if len(ResultCache._shared_cache) <= 5:
                    current_app.logger.info(f"Cache HIT")
                return cached_data['result']
            else:
                # Remove expired cache entry
                del ResultCache._shared_cache[cache_key]
                if current_app.logger.level <= 10:
                    current_app.logger.info(
                        f"Cache EXPIRED for key: {cache_key[:8]}...")
        return None

    def cache_result(self, cache_key, result):
        """Cache the result with timestamp"""
        ResultCache._shared_cache[cache_key] = {
            'result': result,
            'timestamp': time.time()
        }

        # Track stores for this request
        ResultCache._current_request_stores += 1

        # Optimized cache cleanup - remove old entries if cache gets too large
        cache_size = len(ResultCache._shared_cache)
        if cache_size > 2000:  # Increased max cache size
            # Remove oldest 25% of entries efficiently
            current_time = time.time()
            entries_to_remove = []

            for key, data in ResultCache._shared_cache.items():
                # Remove entries at 50% of TTL
                if current_time - data['timestamp'] >= ResultCache._shared_cache_ttl * 0.5:
                    entries_to_remove.append(key)

            # If not enough expired entries, remove oldest ones
            if len(entries_to_remove) < len(ResultCache._shared_cache) * 0.25:
                sorted_keys = sorted(ResultCache._shared_cache.keys(
                ), key=lambda k: ResultCache._shared_cache[k]['timestamp'])
                entries_to_remove.extend(
                    sorted_keys[:max(500, len(ResultCache._shared_cache) // 4)])

            # Limit removal to prevent blocking
            for key in entries_to_remove[:500]:
                ResultCache._shared_cache.pop(key, None)

            if entries_to_remove:
                current_app.logger.info(
                    f"Cache cleanup: removed {min(500, len(entries_to_remove))} entries")

    def get_request_cache_summary(self):
        """Get summary of cache operations for current request"""
        stores = ResultCache._current_request_stores
        total = len(ResultCache._shared_cache)
        ResultCache._current_request_stores = 0  # Reset for next request
        return {'stores': stores, 'total': total}

    def invalidate_cache(self, cache_key=None):
        """Invalidate specific cache entry or all entries"""
        if cache_key:
            ResultCache._shared_cache.pop(cache_key, None)
        else:
            ResultCache._shared_cache.clear()

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

    def _estimate_cache_size(self):
        """Rough estimate of cache size in MB"""
        # This is a very rough estimate
        if not ResultCache._shared_cache:
            return 0.0

        # Sample a few entries to estimate average size
        sample_keys = list(ResultCache._shared_cache.keys())[:10]
        total_size = 0

        for key in sample_keys:
            # Rough estimate: key + result data
            entry_size = len(str(key)) + \
                len(str(ResultCache._shared_cache[key]['result']))
            total_size += entry_size

        if sample_keys:
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
