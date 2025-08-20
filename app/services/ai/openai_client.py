import httpx
import openai
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
                    connect=3.0,     # Increased connect timeout
                    read=30.0,       # Increased read timeout for AI processing
                    write=5.0,
                    pool=2.0
                ),
                limits=httpx.Limits(
                    max_keepalive_connections=200,  # Increased connection pool
                    max_connections=1000,           # Increased total connections
                    keepalive_expiry=300.0          # Longer keepalive
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
        """Test the OpenAI connection with timeout"""
        try:
            if not self.is_configured():
                return False, "API key not configured"

            # Simple test with a minimal request and fast timeout
            model_name = current_app.config.get(
                'OPENAI_CHAT_MODEL', 'gpt-5-2025-08-07')
            response = self.client.chat.completions.create(
                model=model_name,
                messages=[{"role": "user", "content": "hi"}],
                max_tokens=1
            )
            return True, "Connection successful"
        except Exception as e:
            return False, f"Connection failed: {str(e)}"

    def warmup_connection(self):
        """Warm up the connection pool by making a minimal request"""
        if self.is_configured():
            try:
                self.test_connection()
            except Exception:
                # Warmup failures are expected and should be ignored
                pass
