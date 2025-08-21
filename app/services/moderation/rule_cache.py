import time

from flask import current_app

from app.services.database_service import db_service


class CachedRule:
    """Simple data class to hold rule information without SQLAlchemy session dependencies"""

    def __init__(self, id, name, rule_type, action, priority, rule_data):
        self.id = id
        self.name = name
        self.rule_type = rule_type
        self.action = action
        self.priority = priority
        self.rule_data = rule_data

    def __repr__(self):
        return f"CachedRule(id={self.id}, name='{self.name}', type='{self.rule_type}')"


class RuleCache:
    """Manages caching of moderation rules for performance"""

    def __init__(self, cache_ttl=300):  # 5 minutes default
        self._rules_cache = {}
        self._cache_timestamps = {}
        self._cache_ttl = cache_ttl

    async def get_cached_rules(self, project_id):
        """Get rules with caching for performance"""
        current_time = time.time()

        # Check cache
        if (project_id in self._rules_cache and
            project_id in self._cache_timestamps and
                current_time - self._cache_timestamps[project_id] < self._cache_ttl):

            # Using cached rules
            return self._rules_cache[project_id]

        # Fetch from database using centralized service
        try:
            db_rules = await db_service.get_all_rules_for_project(project_id, include_inactive=False)

            # Convert to cache-safe objects
            cached_rules = [
                CachedRule(r.id, r.name, r.rule_type, r.action,
                           r.priority, r.rule_data or {})
                for r in db_rules
            ]

            # Update cache
            self._rules_cache[project_id] = cached_rules
            self._cache_timestamps[project_id] = current_time

            return cached_rules

        except Exception as e:
            current_app.logger.error(f"Error fetching rules: {str(e)}")
            return []

    def invalidate_cache(self, project_id=None):
        """Invalidate cache for a specific project or all projects"""
        if project_id:
            self._rules_cache.pop(project_id, None)
            self._cache_timestamps.pop(project_id, None)
        else:
            self._rules_cache.clear()
            self._cache_timestamps.clear()

    def get_cache_stats(self):
        """Get cache statistics for monitoring"""
        return {
            'cached_projects': len(self._rules_cache),
            'cache_hit_ratio': self._calculate_hit_ratio(),
            'oldest_cache_age': self._get_oldest_cache_age()
        }

    def _calculate_hit_ratio(self):
        """Calculate cache hit ratio (placeholder - would need actual tracking)"""
        # This would require actual hit/miss tracking in production
        return 0.0

    def _get_oldest_cache_age(self):
        """Get age of oldest cache entry in seconds"""
        if not self._cache_timestamps:
            return 0

        current_time = time.time()
        oldest_timestamp = min(self._cache_timestamps.values())
        return current_time - oldest_timestamp
