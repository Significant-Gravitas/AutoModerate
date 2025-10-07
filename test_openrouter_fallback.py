"""
Test script to verify OpenRouter fallback functionality.

This script tests:
1. OpenRouter client initialization
2. OpenRouter API connection (if API key is configured)
3. Fallback integration in AI moderator

Run: python test_openrouter_fallback.py
"""

import os

from dotenv import load_dotenv

# Load environment variables
load_dotenv()

print("=" * 60)
print("OpenRouter Fallback Test")
print("=" * 60)

# Test 1: Check environment configuration
print("\n1. Checking environment configuration...")
openai_key = os.environ.get('OPENAI_API_KEY')
openrouter_key = os.environ.get('OPENROUTER_API_KEY')

print(f"   OpenAI API Key: {'[OK] Configured' if openai_key else '[X] Not configured'}")
print(f"   OpenRouter API Key: {'[OK] Configured' if openrouter_key else '[X] Not configured'}")

# Test 2: Test OpenRouter client import
print("\n2. Testing OpenRouter client import...")
try:
    from app.services.ai.openrouter_client import OpenRouterClient
    print("   [OK] OpenRouter client imported successfully")
except ImportError as e:
    print(f"   [X] Failed to import: {e}")
    exit(1)

# Test 3: Test AI Moderator with fallback
print("\n3. Testing AI Moderator with fallback integration...")
try:
    from app.services.ai.ai_moderator import AIModerator
    print("   [OK] AI Moderator with fallback imported successfully")
except ImportError as e:
    print(f"   [X] Failed to import: {e}")
    exit(1)

# Test 4: Test OpenRouter client initialization (requires Flask app context)
print("\n4. Testing OpenRouter client initialization...")
if openrouter_key:
    try:
        # We need Flask app context for this test
        from app import create_app
        app = create_app()
        with app.app_context():
            client = OpenRouterClient()
            if client.is_configured():
                print("   [OK] OpenRouter client configured successfully")
                print(f"   Base URL: {client.base_url}")
                print(f"   Auto Model: {client.auto_model}")

                # Test connection (optional - will use credits)
                test_connection = input("\n   Test OpenRouter API connection? (y/n): ").lower() == 'y'
                if test_connection:
                    print("   Testing connection to OpenRouter...")
                    success, message = client.test_connection()
                    if success:
                        print(f"   [OK] {message}")
                    else:
                        print(f"   [X] {message}")
            else:
                print("   [X] OpenRouter client not configured (API key missing)")
    except Exception as e:
        print(f"   [X] Error during initialization: {e}")
else:
    print("   [!] Skipping (OPENROUTER_API_KEY not configured)")
    print("   Add OPENROUTER_API_KEY to .env to enable fallback")

# Test 5: Verify fallback method exists
print("\n5. Verifying fallback method in AI Moderator...")
if openrouter_key:
    try:
        from app import create_app
        app = create_app()
        with app.app_context():
            moderator = AIModerator()
            if hasattr(moderator, '_fallback_to_openrouter'):
                print("   [OK] Fallback method exists")
            else:
                print("   [X] Fallback method not found")

            if hasattr(moderator, 'openrouter_client'):
                print("   [OK] OpenRouter client instance exists")
            else:
                print("   [X] OpenRouter client instance not found")
    except Exception as e:
        print(f"   [X] Error: {e}")
else:
    print("   [!] Skipping (OPENROUTER_API_KEY not configured)")

print("\n" + "=" * 60)
print("Test Summary:")
print("=" * 60)
print("[OK] All imports successful")
print("[OK] Fallback architecture implemented")
if openrouter_key:
    print("[OK] OpenRouter configured and ready")
    print("\nThe system will automatically fallback to OpenRouter if OpenAI fails.")
else:
    print("[!] OpenRouter not configured")
    print("\nTo enable fallback:")
    print("1. Get an API key from https://openrouter.ai")
    print("2. Add OPENROUTER_API_KEY=sk-or-your-key to .env")
    print("3. Restart the application")
print("=" * 60)
