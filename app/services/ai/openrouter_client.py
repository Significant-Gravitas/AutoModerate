import threading

import httpx
import openai
from flask import current_app


class OpenRouterClient:
    """Manages OpenRouter client using OpenAI SDK with thread-local storage for thread safety"""

    _thread_local = threading.local()

    def __init__(self):
        try:
            api_key = current_app.config.get('OPENROUTER_API_KEY')

            if not api_key:
                self.api_key = None
            else:
                self.api_key = api_key

            # OpenRouter configuration
            self.base_url = "https://openrouter.ai/api/v1"
            self.auto_model = "openrouter/auto"  # Auto-routing model identifier
        except (ValueError, TypeError, KeyError) as e:
            current_app.logger.error(f"Configuration error for OpenRouter: {str(e)}")
            self.api_key = None

    @classmethod
    def _get_or_create_client(cls, api_key):
        """Create or reuse thread-local OpenAI client configured for OpenRouter"""
        # Check if this thread has a client and if the API key matches
        if not hasattr(cls._thread_local, 'client') or \
           not hasattr(cls._thread_local, 'api_key') or \
           cls._thread_local.api_key != api_key:

            # Create HTTP client with optimized settings
            http_client = httpx.Client(
                timeout=httpx.Timeout(
                    connect=5.0,
                    read=45.0,
                    write=5.0,
                    pool=2.0
                ),
                limits=httpx.Limits(
                    max_keepalive_connections=100,
                    max_connections=500,
                    keepalive_expiry=300.0
                ),
                http2=True
            )

            # Create OpenAI client configured for OpenRouter
            cls._thread_local.client = openai.OpenAI(
                base_url="https://openrouter.ai/api/v1",
                api_key=api_key,
                http_client=http_client
            )
            cls._thread_local.api_key = api_key

        return cls._thread_local.client

    def is_configured(self):
        """Check if OpenRouter client is properly configured"""
        return self.api_key is not None

    def get_client(self):
        """Get the configured OpenAI client for OpenRouter (thread-local)"""
        if not self.is_configured():
            raise Exception("OpenRouter client not configured - API key missing")
        return self._get_or_create_client(self.api_key)

    def test_connection(self):
        """Test the OpenRouter connection"""
        try:
            if not self.is_configured():
                return False, "API key not configured"

            # Simple test with a minimal request
            client = self.get_client()
            response = client.chat.completions.create(
                model=self.auto_model,
                messages=[{"role": "user", "content": "hi"}],
                max_tokens=1
            )

            # Extract model used from response
            model_used = getattr(response, 'model', self.auto_model)

            return True, f"Connection successful (model: {model_used})"

        except (openai.OpenAIError, openai.APIError) as e:
            return False, f"OpenRouter API error: {str(e)}"
        except Exception as e:
            return False, f"OpenRouter error: {str(e)}"
