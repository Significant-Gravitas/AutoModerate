from .moderation_orchestrator import ModerationOrchestrator

class ModerationService:
    """
    DEPRECATED: Backward compatibility wrapper for ModerationOrchestrator
    Please use ModerationOrchestrator directly for new code.
    """
    
    def __init__(self):
        import warnings
        warnings.warn(
            "ModerationService is deprecated. Use ModerationOrchestrator instead.",
            DeprecationWarning,
            stacklevel=2
        )
        self._orchestrator = ModerationOrchestrator()
    
    def moderate_content(self, content_id, request_start_time=None):
        """Delegate to ModerationOrchestrator"""
        return self._orchestrator.moderate_content(content_id, request_start_time)
    
    def get_project_stats(self, project_id):
        """Delegate to ModerationOrchestrator"""
        return self._orchestrator.get_project_stats(project_id)