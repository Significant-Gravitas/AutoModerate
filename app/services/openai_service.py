from .ai.ai_moderator import AIModerator

class OpenAIService:
    """
    DEPRECATED: Backward compatibility wrapper for AIModerator
    Please use AIModerator directly for new code.
    """
    
    def __init__(self):
        import warnings
        warnings.warn(
            "OpenAIService is deprecated. Use AIModerator instead.",
            DeprecationWarning,
            stacklevel=2
        )
        self._ai_moderator = AIModerator()
    
    def moderate_content(self, content, content_type='text', custom_prompt=None):
        """Delegate to AIModerator"""
        return self._ai_moderator.moderate_content(content, content_type, custom_prompt)
    
    def get_moderation_categories_info(self):
        """Delegate to AIModerator"""
        return self._ai_moderator.get_moderation_categories_info()