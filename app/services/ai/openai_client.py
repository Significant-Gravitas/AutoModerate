import openai
import httpx
from flask import current_app

class OpenAIClient:
    """Manages OpenAI client configuration and connection pooling"""
    
    _client = None
    _api_key = None
    
    def __init__(self):
        try:
            api_key = current_app.config.get('OPENAI_API_KEY')
            
            if not api_key:
                self.api_key = None
                self.client = None
            else:
                self.api_key = api_key
                self.client = self._get_or_create_client(api_key)
        except Exception as e:
            current_app.logger.error(f"Failed to configure OpenAI: {str(e)}")
            self.api_key = None
            self.client = None
    
    @classmethod
    def _get_or_create_client(cls, api_key):
        """Create or reuse OpenAI client with optimized settings for speed"""
        if cls._client is None or cls._api_key != api_key:
            http_client = httpx.Client(
                timeout=httpx.Timeout(
                    connect=1.0,
                    read=8.0, 
                    write=2.0,
                    pool=1.0 
                ),
                limits=httpx.Limits(
                    max_keepalive_connections=100,
                    max_connections=500,
                    keepalive_expiry=120.0
                ),
                http2=True
            )
            
            cls._client = openai.OpenAI(
                api_key=api_key,
                http_client=http_client
            )
            cls._api_key = api_key
        
        return cls._client
    
    def is_configured(self):
        """Check if OpenAI client is properly configured"""
        return self.api_key is not None and self.client is not None
    
    def get_client(self):
        """Get the configured OpenAI client"""
        if not self.is_configured():
            raise Exception("OpenAI client not configured - API key missing")
        return self.client
    
    def test_connection(self):
        """Test the OpenAI connection"""
        try:
            if not self.is_configured():
                return False, "API key not configured"
            
            # Simple test with a minimal request
            model_name = current_app.config.get('OPENAI_CHAT_MODEL', 'gpt-5-2025-08-07')
            response = self.client.chat.completions.create(
                model=model_name,
                messages=[{"role": "user", "content": "test"}],
            )
            return True, "Connection successful"
        except Exception as e:
            return False, f"Connection failed: {str(e)}"