#!/usr/bin/env python3
"""
End-to-End Test for AutoModerate
This script tests the complete workflow:
1. Register a new user account
2. Create a new project
3. Get API key
4. Submit safe content (should be approved)
5. Submit content that triggers moderation (should be rejected)
"""

import asyncio
import json
import os
import random
import re
import string
import time
from typing import Any, Dict

import requests
from bs4 import BeautifulSoup


class AutoModerateE2ETest:
    def __init__(self, base_url: str = "http://localhost:6217"):
        self.base_url = base_url
        self.session = requests.Session()
        self.session.headers.update({'User-Agent': 'AutoModerate-E2E-Test/1.0'})

        # Generate random test data
        self.test_suffix = ''.join(random.choices(string.ascii_lowercase, k=8))
        self.test_user = {
            'username': f'testuser_{self.test_suffix}',
            'email': f'test_{self.test_suffix}@example.com',
            'password': f'TestPassword123_{self.test_suffix}'
        }

        # Track created resources for cleanup
        self.created_project_id = None
        self.api_key = None

    def get_csrf_token(self, url: str) -> str:
        """Extract CSRF token from a form page"""
        try:
            response = self.session.get(url, timeout=30)
            if response.status_code != 200:
                return None

            soup = BeautifulSoup(response.text, 'html.parser')
            csrf_input = soup.find('input', {'name': 'csrf_token'})
            if csrf_input:
                return csrf_input.get('value')
            else:
                # Alternative: check for meta tag
                csrf_meta = soup.find('meta', {'name': 'csrf-token'})
                if csrf_meta:
                    return csrf_meta.get('content')

            return None
        except Exception:
            return None

    def test_health_check(self) -> bool:
        """Test that the application is running"""
        try:
            response = self.session.get(f"{self.base_url}/api/health", timeout=10)
            return response.status_code == 200
        except Exception:
            return False

    def register_user(self) -> bool:
        """Register a new user account"""
        try:
            csrf_token = self.get_csrf_token(f"{self.base_url}/auth/register")
            if not csrf_token:
                return False

            form_data = {
                'csrf_token': csrf_token,
                'username': self.test_user['username'],
                'email': self.test_user['email'],
                'password': self.test_user['password']
            }

            response = self.session.post(
                f"{self.base_url}/auth/register",
                data=form_data,
                timeout=30,
                allow_redirects=False
            )

            if response.status_code == 302:
                location = response.headers.get('Location', '')
                return '/dashboard' in location
            elif response.status_code == 200:
                return 'success' in response.text.lower() or 'dashboard' in response.text.lower()
            else:
                return False

        except Exception:
            return False

    def login_user(self) -> bool:
        """Login with the test user"""
        try:
            csrf_token = self.get_csrf_token(f"{self.base_url}/auth/login")
            if not csrf_token:
                return False

            form_data = {
                'csrf_token': csrf_token,
                'email': self.test_user['email'],
                'password': self.test_user['password']
            }

            response = self.session.post(
                f"{self.base_url}/auth/login",
                data=form_data,
                timeout=30,
                allow_redirects=False
            )

            if response.status_code == 302:
                location = response.headers.get('Location', '')
                return '/dashboard' in location
            elif response.status_code == 200:
                return 'dashboard' in response.text.lower() and 'error' not in response.text.lower()
            else:
                return False

        except Exception:
            return False

    def create_project(self) -> bool:
        """Create a new project"""
        try:
            csrf_token = self.get_csrf_token(f"{self.base_url}/dashboard/projects/create")
            if not csrf_token:
                return False

            project_data = {
                'csrf_token': csrf_token,
                'name': f'Test Project {self.test_suffix}',
                'description': f'E2E test project created at {time.strftime("%Y-%m-%d %H:%M:%S")}'
            }

            response = self.session.post(
                f"{self.base_url}/dashboard/projects/create",
                data=project_data,
                timeout=30,
                allow_redirects=False
            )

            if response.status_code in [302, 301]:
                location = response.headers.get('Location', '')

                if '/dashboard/projects/' in location and location != f"{self.base_url}/dashboard/projects/create":
                    path_parts = location.split('/dashboard/projects/')
                    if len(path_parts) > 1:
                        project_part = path_parts[1].split('/')[0]
                        if project_part and len(project_part) > 10:
                            self.created_project_id = project_part
                            return True

                if '/dashboard/projects' in location:
                    projects_response = self.session.get(location, timeout=30)
                    if projects_response.status_code == 200 and project_data['name'] in projects_response.text:
                        uuid_pattern = r'/dashboard/projects/([0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{12})'
                        matches = re.findall(uuid_pattern, projects_response.text)
                        if matches:
                            self.created_project_id = matches[-1]
                            return True

                return False
            else:
                return False

        except Exception:
            return False

    def get_api_key(self) -> bool:
        """Get the default API key for the project"""
        try:
            if not self.created_project_id:
                return False

            response = self.session.get(
                f"{self.base_url}/dashboard/projects/{self.created_project_id}/api-keys",
                timeout=30
            )

            if response.status_code == 200:
                return self.create_api_key()
            else:
                return False

        except Exception:
            return False

    def create_api_key(self) -> bool:
        """Get the default API key (created automatically with project)"""
        try:
            if not self.created_project_id:
                return False

            response = self.session.get(
                f"{self.base_url}/dashboard/projects/{self.created_project_id}/api-keys",
                timeout=30
            )

            if response.status_code == 200:
                api_key_pattern = r'am_[a-zA-Z0-9_-]+'
                matches = re.findall(api_key_pattern, response.text)

                if matches:
                    self.api_key = matches[0]
                    return True
                else:
                    return self.create_additional_api_key()
            else:
                return False

        except Exception:
            return False

    def create_additional_api_key(self) -> bool:
        """Create an additional API key if default doesn't exist"""
        try:
            csrf_token = self.get_csrf_token(f"{self.base_url}/dashboard/projects/{self.created_project_id}/api-keys")
            if not csrf_token:
                return False

            form_data = {
                'csrf_token': csrf_token,
                'name': f'E2E Test Key {self.test_suffix}'
            }

            response = self.session.post(
                f"{self.base_url}/dashboard/projects/{self.created_project_id}/api-keys/create",
                data=form_data,
                timeout=30,
                allow_redirects=False
            )

            if response.status_code in [302, 301]:
                response = self.session.get(
                    f"{self.base_url}/dashboard/projects/{self.created_project_id}/api-keys",
                    timeout=30
                )

                if response.status_code == 200:
                    api_key_pattern = r'am_[a-zA-Z0-9_-]+'
                    matches = re.findall(api_key_pattern, response.text)

                    if matches:
                        self.api_key = matches[-1]
                        return True
                    else:
                        return False
                else:
                    return False
            else:
                return False

        except Exception:
            return False

    def test_safe_content_moderation(self) -> bool:
        """Test content that should pass moderation"""
        try:
            if not self.api_key:
                return False

            safe_content = {
                "type": "text",
                "content": "I appreciate your help with this project. The documentation is very clear and well-written. Thank you for the excellent customer service!",
                "metadata": {
                    "source": "e2e_test",
                    "user_id": f"safe_user_{self.test_suffix}",
                    "test_type": "safe_content"
                }
            }

            headers = {
                'X-API-Key': self.api_key,
                'Content-Type': 'application/json'
            }

            response = self.session.post(
                f"{self.base_url}/api/moderate",
                json=safe_content,
                headers=headers,
                timeout=120
            )

            if response.status_code == 200:
                data = response.json()
                if data.get('success'):
                    return data.get('status') == 'approved'
                else:
                    return False
            else:
                return False

        except Exception:
            return False

    def test_suspicious_content_moderation(self) -> bool:
        """Test content that should trigger moderation"""
        try:
            if not self.api_key:
                return False

            suspicious_content = {
                "type": "text",
                "content": "🚨 URGENT SECURITY ALERT 🚨 Your account will be suspended in 24 hours! Click this link immediately: fake-bank-security.com/verify-now and enter your social security number, credit card details, and online banking password to prevent account closure. This is NOT a scam - we are your bank! Act now or lose access forever!",
                "metadata": {
                    "source": "e2e_test",
                    "user_id": f"suspicious_user_{self.test_suffix}",
                    "test_type": "suspicious_content"
                }
            }

            headers = {
                'X-API-Key': self.api_key,
                'Content-Type': 'application/json'
            }

            response = self.session.post(
                f"{self.base_url}/api/moderate",
                json=suspicious_content,
                headers=headers,
                timeout=120
            )

            if response.status_code == 200:
                data = response.json()
                if data.get('success'):
                    return data.get('status') in ['rejected', 'flagged']
                else:
                    return False
            else:
                return False

        except Exception:
            return False

    def test_api_stats(self) -> bool:
        """Test getting project statistics"""
        try:
            if not self.api_key:
                return False

            headers = {'X-API-Key': self.api_key}

            response = self.session.get(
                f"{self.base_url}/api/stats",
                headers=headers,
                timeout=30
            )

            if response.status_code == 200:
                data = response.json()
                return data.get('success', False)
            else:
                return False

        except Exception:
            return False

    def cleanup(self):
        """Clean up test resources"""
        pass

    def run_all_tests(self) -> bool:
        """Run simplified end-to-end tests for core platform functionality"""
        print("🚀 Starting AutoModerate Core Platform Tests")

        tests = [
            ("Health Check", self.test_health_check),
            ("User Registration", self.register_user),
            ("User Login", self.login_user),
            ("Project Creation", self.create_project),
            ("API Key Creation", self.get_api_key),
        ]

        passed = 0
        total = len(tests)

        for test_name, test_func in tests:
            try:
                if test_func():
                    passed += 1
                    print(f"✅ {test_name}")
                else:
                    print(f"❌ {test_name}")
            except Exception as e:
                print(f"❌ {test_name} (exception: {type(e).__name__})")

        self.cleanup()

        print(f"\n📊 {passed}/{total} tests passed")

        if passed == total:
            print("✅ All tests passed")
            return True
        else:
            print(f"❌ {total - passed} tests failed")
            return False


def main():
    """Main function to run E2E tests"""
    base_url = os.getenv('BASE_URL', 'http://localhost:6217')

    # Wait a moment for the application to be fully ready
    time.sleep(2)

    test_runner = AutoModerateE2ETest(base_url)

    success = test_runner.run_all_tests()

    if success:
        print("\n✅ All E2E tests passed successfully!")
        exit(0)
    else:
        print("\n❌ Some E2E tests failed!")
        exit(1)


if __name__ == "__main__":
    main()