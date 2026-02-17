#!/usr/bin/env python3
"""
E2E Tests for AutoModerate

Tests the complete content moderation workflow:
- Platform health & auth
- Project and API key management
- Content moderation (safe + suspicious content)
- Stats endpoint

Run with: python tests/e2e_test.py
Or: pytest tests/e2e_test.py -v
"""

import os
import random
import re
import string
import sys
import time

import requests
from bs4 import BeautifulSoup


class AutoModerateClient:
    """HTTP client for AutoModerate with session management."""

    def __init__(self, base_url: str = "http://localhost:6217"):
        self.base_url = base_url.rstrip("/")
        self.session = requests.Session()
        self.session.headers.update({"User-Agent": "AutoModerate-E2E-Test/2.0"})

    def get(self, path: str, **kwargs) -> requests.Response:
        return self.session.get(f"{self.base_url}{path}", timeout=30, **kwargs)

    def post(self, path: str, **kwargs) -> requests.Response:
        return self.session.post(f"{self.base_url}{path}", timeout=30, **kwargs)

    def get_csrf_token(self, path: str) -> str | None:
        """Extract CSRF token from a form page."""
        resp = self.get(path, allow_redirects=False)
        if resp.status_code != 200:
            return None

        soup = BeautifulSoup(resp.text, "html.parser")

        # Try input field first
        csrf_input = soup.find("input", {"name": "csrf_token"})
        if csrf_input:
            return csrf_input.get("value")

        # Try meta tag
        csrf_meta = soup.find("meta", {"name": "csrf-token"})
        if csrf_meta:
            return csrf_meta.get("content")

        return None

    def api_get(self, path: str, api_key: str, **kwargs) -> requests.Response:
        headers = kwargs.pop("headers", {})
        headers["X-API-Key"] = api_key
        return self.get(path, headers=headers, **kwargs)

    def api_post(self, path: str, api_key: str, **kwargs) -> requests.Response:
        headers = kwargs.pop("headers", {})
        headers["X-API-Key"] = api_key
        headers["Content-Type"] = "application/json"
        return self.post(path, headers=headers, **kwargs)


class TestResult:
    """Simple test result tracker."""

    def __init__(self):
        self.passed = 0
        self.failed = 0
        self.results = []

    def ok(self, name: str):
        self.passed += 1
        self.results.append((name, True, None))
        print(f"  ✓ {name}")

    def fail(self, name: str, reason: str = ""):
        self.failed += 1
        self.results.append((name, False, reason))
        print(f"  ✗ {name}" + (f" — {reason}" if reason else ""))

    @property
    def success(self) -> bool:
        return self.failed == 0

    def summary(self) -> str:
        total = self.passed + self.failed
        return f"{self.passed}/{total} tests passed"


def random_suffix(length: int = 8) -> str:
    return "".join(random.choices(string.ascii_lowercase, k=length))


# =============================================================================
# Test Functions
# =============================================================================


def test_health(client: AutoModerateClient, results: TestResult):
    """Test that the application is running and healthy."""
    try:
        resp = client.get("/api/health")
        if resp.status_code == 200:
            results.ok("health check")
        else:
            results.fail("health check", f"status {resp.status_code}")
    except Exception as e:
        results.fail("health check", str(e))


def test_register_and_auth(client: AutoModerateClient, results: TestResult) -> dict | None:
    """Register a new user and verify authentication works."""
    suffix = random_suffix()
    user = {
        "username": f"testuser_{suffix}",
        "email": f"test_{suffix}@example.com",
        "password": f"TestPass123_{suffix}",
    }

    try:
        # Get CSRF token
        csrf = client.get_csrf_token("/auth/register")
        if not csrf:
            results.fail("register", "couldn't get CSRF token")
            return None

        # Register
        resp = client.post(
            "/auth/register",
            data={**user, "csrf_token": csrf},
            allow_redirects=False,
        )

        # Should redirect to dashboard (registration auto-logs in)
        if resp.status_code == 302 and "/dashboard" in resp.headers.get("Location", ""):
            results.ok("register + auto-login")
            return user
        else:
            results.fail("register", f"unexpected response: {resp.status_code}")
            return None

    except Exception as e:
        results.fail("register", str(e))
        return None


def test_create_project(client: AutoModerateClient, results: TestResult) -> str | None:
    """Create a new project and return its ID."""
    suffix = random_suffix()

    try:
        csrf = client.get_csrf_token("/dashboard/projects/create")
        if not csrf:
            results.fail("create project", "couldn't get CSRF token (not logged in?)")
            return None

        resp = client.post(
            "/dashboard/projects/create",
            data={
                "csrf_token": csrf,
                "name": f"Test Project {suffix}",
                "description": f"E2E test project {suffix}",
            },
            allow_redirects=False,
        )

        if resp.status_code not in (301, 302):
            results.fail("create project", f"unexpected status: {resp.status_code}")
            return None

        location = resp.headers.get("Location", "")

        # Extract project UUID from redirect
        uuid_match = re.search(
            r"/dashboard/projects/([0-9a-fA-F-]{36})", location
        )
        if uuid_match:
            project_id = uuid_match.group(1)
            results.ok("create project")
            return project_id

        # Sometimes redirects to project list — fetch and find it
        if "/dashboard/projects" in location:
            list_resp = client.get("/dashboard/projects")
            uuid_match = re.search(
                r"/dashboard/projects/([0-9a-fA-F-]{36})", list_resp.text
            )
            if uuid_match:
                project_id = uuid_match.group(1)
                results.ok("create project")
                return project_id

        results.fail("create project", "couldn't extract project ID")
        return None

    except Exception as e:
        results.fail("create project", str(e))
        return None


def test_get_api_key(client: AutoModerateClient, results: TestResult, project_id: str) -> str | None:
    """Get or create an API key for the project."""
    try:
        resp = client.get(f"/dashboard/projects/{project_id}/api-keys")
        if resp.status_code != 200:
            results.fail("get API key", f"couldn't access API keys page: {resp.status_code}")
            return None

        # Look for existing API key
        key_match = re.search(r"(am_[a-zA-Z0-9_-]+)", resp.text)
        if key_match:
            results.ok("get API key")
            return key_match.group(1)

        # Create one if none exists
        csrf = client.get_csrf_token(f"/dashboard/projects/{project_id}/api-keys")
        if not csrf:
            results.fail("get API key", "no existing key and couldn't get CSRF to create one")
            return None

        create_resp = client.post(
            f"/dashboard/projects/{project_id}/api-keys/create",
            data={"csrf_token": csrf, "name": f"E2E Test Key {random_suffix()}"},
            allow_redirects=True,
        )

        key_match = re.search(r"(am_[a-zA-Z0-9_-]+)", create_resp.text)
        if key_match:
            results.ok("get API key (created)")
            return key_match.group(1)

        results.fail("get API key", "couldn't create API key")
        return None

    except Exception as e:
        results.fail("get API key", str(e))
        return None


def test_moderate_safe_content(client: AutoModerateClient, results: TestResult, api_key: str):
    """Test that safe content is approved."""
    try:
        resp = client.api_post(
            "/api/moderate",
            api_key,
            json={
                "type": "text",
                "content": "Thank you for your excellent customer service! The documentation is clear and helpful.",
                "metadata": {"source": "e2e_test", "test_type": "safe"},
            },
        )

        if resp.status_code != 200:
            results.fail("moderate safe content", f"status {resp.status_code}")
            return

        data = resp.json()
        if data.get("success") and data.get("status") == "approved":
            results.ok("moderate safe content → approved")
        else:
            results.fail("moderate safe content", f"expected approved, got: {data}")

    except Exception as e:
        results.fail("moderate safe content", str(e))


def test_moderate_suspicious_content(client: AutoModerateClient, results: TestResult, api_key: str):
    """Test that suspicious/harmful content is flagged or rejected."""
    try:
        resp = client.api_post(
            "/api/moderate",
            api_key,
            json={
                "type": "text",
                "content": (
                    "🚨 URGENT: Your account will be SUSPENDED! "
                    "Click here immediately: fake-bank.com/verify "
                    "Enter your SSN, credit card, and password NOW or lose access forever!"
                ),
                "metadata": {"source": "e2e_test", "test_type": "suspicious"},
            },
        )

        if resp.status_code != 200:
            results.fail("moderate suspicious content", f"status {resp.status_code}")
            return

        data = resp.json()
        if data.get("success") and data.get("status") in ("rejected", "flagged"):
            results.ok(f"moderate suspicious content → {data.get('status')}")
        else:
            results.fail("moderate suspicious content", f"expected rejected/flagged, got: {data}")

    except Exception as e:
        results.fail("moderate suspicious content", str(e))


def test_api_stats(client: AutoModerateClient, results: TestResult, api_key: str):
    """Test the stats endpoint returns valid data."""
    try:
        resp = client.api_get("/api/stats", api_key)

        if resp.status_code != 200:
            results.fail("API stats", f"status {resp.status_code}")
            return

        data = resp.json()
        if data.get("success"):
            results.ok("API stats")
        else:
            results.fail("API stats", f"success=false: {data}")

    except Exception as e:
        results.fail("API stats", str(e))


# =============================================================================
# Main Runner
# =============================================================================


def run_tests(base_url: str = "http://localhost:6217", include_moderation: bool = True) -> bool:
    """
    Run the E2E test suite.

    Args:
        base_url: AutoModerate server URL
        include_moderation: Whether to run moderation tests (requires OpenAI key)

    Returns:
        True if all tests passed
    """
    print(f"\n{'='*60}")
    print("AutoModerate E2E Tests")
    print(f"{'='*60}")
    print(f"Target: {base_url}")
    print()

    client = AutoModerateClient(base_url)
    results = TestResult()

    # Phase 1: Platform Core
    print("▸ Platform Core")
    test_health(client, results)

    user = test_register_and_auth(client, results)
    if not user:
        print(f"\n{results.summary()}")
        print("⚠ Stopping early — auth failed\n")
        return False

    project_id = test_create_project(client, results)
    if not project_id:
        print(f"\n{results.summary()}")
        print("⚠ Stopping early — project creation failed\n")
        return False

    api_key = test_get_api_key(client, results, project_id)
    if not api_key:
        print(f"\n{results.summary()}")
        print("⚠ Stopping early — API key retrieval failed\n")
        return False

    # Phase 2: Moderation API
    if include_moderation:
        print("\n▸ Moderation API")
        test_moderate_safe_content(client, results, api_key)
        test_moderate_suspicious_content(client, results, api_key)
        test_api_stats(client, results, api_key)
    else:
        print("\n▸ Moderation API (skipped — no OpenAI key)")

    # Summary
    print(f"\n{'='*60}")
    print(results.summary())
    if results.success:
        print("✅ All tests passed!")
    else:
        print("❌ Some tests failed")
    print(f"{'='*60}\n")

    return results.success


def main():
    base_url = os.getenv("BASE_URL", "http://localhost:6217")

    # Check if we should run moderation tests
    # In CI with a test key, moderation will fail — skip those tests
    openai_key = os.getenv("OPENAI_API_KEY", "")
    include_moderation = openai_key and not openai_key.startswith("test")

    # Give the app a moment to be fully ready
    time.sleep(1)

    success = run_tests(base_url, include_moderation=include_moderation)
    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()
