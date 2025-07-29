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
            # Create HTTP client with AGGRESSIVE connection pooling for maximum throughput
            http_client = httpx.Client(
                timeout=httpx.Timeout(
                    connect=2.0,    # Faster connection timeout
                    read=25.0,      # Slightly reduced read timeout
                    write=5.0,      # Faster write timeout
                    pool=2.0        # Much faster pool timeout
                ),
                limits=httpx.Limits(
                    max_keepalive_connections=50,  # More keep-alive connections
                    max_connections=200,           # Higher connection limit for load
                    keepalive_expiry=60.0         # Longer keep-alive for reuse
                ),
                # Enable HTTP/2 for better multiplexing
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
            response = self.client.chat.completions.create(
                model="gpt-3.5-turbo",
                messages=[{"role": "user", "content": "test"}],
                max_tokens=1
            )
            return True, "Connection successful"
        except Exception as e:
            return False, f"Connection failed: {str(e)}"