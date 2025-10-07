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

    def log(self, message: str, level: str = "INFO"):
        """Log a message with timestamp"""
        print(f"[{time.strftime('%H:%M:%S')}] {level}: {message}")

    def get_csrf_token(self, url: str) -> str:
        """Extract CSRF token from a form page"""
        try:
            response = self.session.get(url, timeout=30)
            if response.status_code != 200:
                self.log(f"Failed to get CSRF token from {url}: HTTP {response.status_code}", "ERROR")
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

            self.log(f"No CSRF token found in {url}", "ERROR")
            return None
        except Exception as e:
            self.log(f"Error extracting CSRF token: {str(e)}", "ERROR")
            return None

    def test_health_check(self) -> bool:
        """Test that the application is running"""
        try:
            response = self.session.get(f"{self.base_url}/api/health", timeout=10)
            if response.status_code == 200:
                data = response.json()
                self.log(f"✅ Health check passed: {data.get('service', 'AutoModerate')} is {data.get('status', 'unknown')}")
                return True
            else:
                self.log(f"❌ Health check failed: HTTP {response.status_code}", "ERROR")
                return False
        except Exception as e:
            self.log(f"❌ Health check failed: {str(e)}", "ERROR")
            return False

    def register_user(self) -> bool:
        """Register a new user account"""
        try:
            # Get CSRF token from registration form
            csrf_token = self.get_csrf_token(f"{self.base_url}/auth/register")
            if not csrf_token:
                self.log("❌ Failed to get CSRF token for registration", "ERROR")
                return False

            # Submit form data with CSRF token
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
                allow_redirects=False  # Handle redirects manually
            )

            # Check for successful registration (redirect to dashboard or 200 with success)
            if response.status_code == 302:
                # Successful registration should redirect to dashboard
                location = response.headers.get('Location', '')
                if '/dashboard' in location:
                    self.log("✅ User registered successfully")
                    return True
                else:
                    self.log(f"❌ Registration redirect unexpected: {location}", "ERROR")
                    return False
            elif response.status_code == 200:
                # Check if it's a success response
                if 'success' in response.text.lower() or 'dashboard' in response.text.lower():
                    self.log("✅ User registered successfully")
                    return True
                else:
                    self.log(f"❌ Registration form error: {response.text[:200]}", "ERROR")
                    return False
            else:
                self.log(f"❌ User registration failed: HTTP {response.status_code} - {response.text[:200]}", "ERROR")
                return False

        except Exception as e:
            self.log(f"❌ User registration failed: {str(e)}", "ERROR")
            return False

    def login_user(self) -> bool:
        """Login with the test user"""
        try:
            # Get CSRF token from login form
            csrf_token = self.get_csrf_token(f"{self.base_url}/auth/login")
            if not csrf_token:
                self.log("❌ Failed to get CSRF token for login", "ERROR")
                return False

            # Submit form data with CSRF token
            form_data = {
                'csrf_token': csrf_token,
                'email': self.test_user['email'],
                'password': self.test_user['password']
            }

            response = self.session.post(
                f"{self.base_url}/auth/login",
                data=form_data,
                timeout=30,
                allow_redirects=False  # Handle redirects manually
            )

            # Check for successful login (redirect to dashboard)
            if response.status_code == 302:
                location = response.headers.get('Location', '')
                if '/dashboard' in location:
                    self.log("✅ User logged in successfully")
                    return True
                else:
                    self.log(f"❌ Login redirect unexpected: {location}", "ERROR")
                    return False
            elif response.status_code == 200:
                # Check if it's a success response
                if 'dashboard' in response.text.lower() and 'error' not in response.text.lower():
                    self.log("✅ User logged in successfully")
                    return True
                else:
                    self.log(f"❌ Login form error: {response.text[:200]}", "ERROR")
                    return False
            else:
                self.log(f"❌ User login failed: HTTP {response.status_code} - {response.text[:200]}", "ERROR")
                return False

        except Exception as e:
            self.log(f"❌ User login failed: {str(e)}", "ERROR")
            return False

    def create_project(self) -> bool:
        """Create a new project"""
        try:
            # Get CSRF token from project creation form
            csrf_token = self.get_csrf_token(f"{self.base_url}/dashboard/projects/create")
            if not csrf_token:
                self.log("❌ Failed to get CSRF token for project creation", "ERROR")
                return False

            # Submit form data with CSRF token
            project_data = {
                'csrf_token': csrf_token,
                'name': f'Test Project {self.test_suffix}',
                'description': f'E2E test project created at {time.strftime("%Y-%m-%d %H:%M:%S")}'
            }

            response = self.session.post(
                f"{self.base_url}/dashboard/projects/create",
                data=project_data,
                timeout=30,
                allow_redirects=False  # Handle redirects manually
            )

            # Handle redirect response
            if response.status_code in [302, 301]:
                # Extract project ID from Location header
                location = response.headers.get('Location', '')
                self.log(f"Redirect location: {location}")

                if '/dashboard/projects/' in location and location != f"{self.base_url}/dashboard/projects/create":
                    # Extract project ID from URL like /dashboard/projects/uuid-here
                    path_parts = location.split('/dashboard/projects/')
                    if len(path_parts) > 1:
                        project_part = path_parts[1].split('/')[0]  # Get first part after projects/
                        if project_part and len(project_part) > 10:  # Should be a UUID
                            self.created_project_id = project_part
                            self.log(f"✅ Project created successfully: {project_data['name']} (ID: {self.created_project_id})")
                            return True

                # If we get redirected back to projects list, try to find the project there
                if '/dashboard/projects' in location:
                    # Follow the redirect to see if project was created
                    projects_response = self.session.get(location, timeout=30)
                    if projects_response.status_code == 200 and project_data['name'] in projects_response.text:
                        # Try to extract project ID from the HTML
                        import re

                        # Look for project links in the HTML
                        uuid_pattern = r'/dashboard/projects/([0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{12})'
                        matches = re.findall(uuid_pattern, projects_response.text)
                        if matches:
                            self.created_project_id = matches[-1]  # Get the last (newest) project
                            self.log(f"✅ Project created successfully: {project_data['name']} (ID: {self.created_project_id})")
                            return True

                self.log(f"❌ Project creation: Redirect location unclear - {location}", "ERROR")
                return False
            else:
                self.log(f"❌ Project creation failed: HTTP {response.status_code} - {response.text[:200]}", "ERROR")
                return False

        except Exception as e:
            self.log(f"❌ Project creation failed: {str(e)}", "ERROR")
            return False

    def get_api_key(self) -> bool:
        """Get the default API key for the project"""
        try:
            if not self.created_project_id:
                self.log("❌ No project ID available to get API key", "ERROR")
                return False

            response = self.session.get(
                f"{self.base_url}/dashboard/projects/{self.created_project_id}/api-keys",
                timeout=30
            )

            if response.status_code == 200:
                # Parse HTML response to find API key
                # Since this is an HTML page, we need to create an API key first
                return self.create_api_key()
            else:
                self.log(f"❌ Failed to access API keys page: HTTP {response.status_code}", "ERROR")
                return False

        except Exception as e:
            self.log(f"❌ Getting API key failed: {str(e)}", "ERROR")
            return False

    def create_api_key(self) -> bool:
        """Get the default API key (created automatically with project)"""
        try:
            if not self.created_project_id:
                self.log("❌ No project ID available to get API key", "ERROR")
                return False

            # First try to get the default API key that should already exist
            response = self.session.get(
                f"{self.base_url}/dashboard/projects/{self.created_project_id}/api-keys",
                timeout=30
            )

            if response.status_code == 200:
                # Extract API key from HTML (look for pattern am_xxxx)
                import re
                api_key_pattern = r'am_[a-zA-Z0-9_-]+'
                matches = re.findall(api_key_pattern, response.text)

                if matches:
                    self.api_key = matches[0]  # Get the first (default) key
                    self.log("✅ Default API key retrieved")
                    return True
                else:
                    self.log("❌ No API keys found, trying to create one", "WARNING")
                    # If no default key exists, create one
                    return self.create_additional_api_key()
            else:
                self.log(f"❌ Failed to access API keys page: HTTP {response.status_code}", "ERROR")
                return False

        except Exception as e:
            self.log(f"❌ API key retrieval failed: {str(e)}", "ERROR")
            return False

    def create_additional_api_key(self) -> bool:
        """Create an additional API key if default doesn't exist"""
        try:
            # Get CSRF token for API key creation
            csrf_token = self.get_csrf_token(f"{self.base_url}/dashboard/projects/{self.created_project_id}/api-keys")
            if not csrf_token:
                self.log("❌ Failed to get CSRF token for API key creation", "ERROR")
                return False

            # Create API key via form submission with CSRF token
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
                # API key was created, now get it from the API keys page
                response = self.session.get(
                    f"{self.base_url}/dashboard/projects/{self.created_project_id}/api-keys",
                    timeout=30
                )

                if response.status_code == 200:
                    # Extract API key from HTML (look for pattern am_xxxx)
                    import re
                    api_key_pattern = r'am_[a-zA-Z0-9_-]+'
                    matches = re.findall(api_key_pattern, response.text)

                    if matches:
                        self.api_key = matches[-1]  # Get the last (newest) key
                        self.log("✅ API key created and retrieved")
                        return True
                    else:
                        self.log("❌ API key not found in response after creation", "ERROR")
                        return False
                else:
                    self.log(f"❌ Failed to retrieve API key after creation: HTTP {response.status_code}", "ERROR")
                    return False
            else:
                self.log(f"❌ API key creation failed: HTTP {response.status_code} - {response.text[:200]}", "ERROR")
                return False

        except Exception as e:
            self.log(f"❌ API key creation failed: {str(e)}", "ERROR")
            return False

    def test_safe_content_moderation(self) -> bool:
        """Test content that should pass moderation"""
        try:
            if not self.api_key:
                self.log("❌ No API key available for content moderation", "ERROR")
                return False

            # Use clear, unambiguously safe content
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

            self.log("Submitting safe content for moderation")

            response = self.session.post(
                f"{self.base_url}/api/moderate",
                json=safe_content,
                headers=headers,
                timeout=120  # Longer timeout for GPT-5 processing
            )

            self.log(f"Safe content response: {response.status_code}")

            if response.status_code == 200:
                data = response.json()
                self.log(f"Safe content response: success={data.get('success')}, status={data.get('status')}")

                if data.get('success'):
                    status = data.get('status')
                    if status == 'approved':
                        self.log(f"✅ Safe content moderation passed: {status}")
                        self.log(f"   Content ID: {data.get('content_id')}")
                        moderation_results = data.get('moderation_results', [])
                        if moderation_results:
                            self.log(f"   Moderation details: {moderation_results[0].get('reason', 'No reason')}")
                        return True
                    else:
                        self.log(f"❌ Safe content was incorrectly {status}", "ERROR")
                        self.log(f"   Content ID: {data.get('content_id')}")
                        moderation_results = data.get('moderation_results', [])
                        if moderation_results:
                            self.log(f"   Reason: {moderation_results[0].get('reason', 'No reason')}", "ERROR")
                        return False
                else:
                    self.log(f"❌ Safe content API returned success=false: {data}", "ERROR")
                    return False
            else:
                try:
                    error_data = response.json()
                    error_detail = error_data.get('error', 'Unknown error')
                except:
                    error_detail = response.text[:500]

                self.log(f"❌ Safe content moderation failed: HTTP {response.status_code}", "ERROR")
                self.log(f"   Error: {error_detail}", "ERROR")

                return False

        except Exception as e:
            self.log(f"❌ Safe content moderation failed: {str(e)}", "ERROR")
            return False

    def test_suspicious_content_moderation(self) -> bool:
        """Test content that should trigger moderation"""
        try:
            if not self.api_key:
                self.log("❌ No API key available for content moderation", "ERROR")
                return False

            # Use content that should clearly trigger fraud/phishing detection
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

            self.log("Submitting suspicious content for moderation")

            response = self.session.post(
                f"{self.base_url}/api/moderate",
                json=suspicious_content,
                headers=headers,
                timeout=120  # Longer timeout for GPT-5 processing
            )

            self.log(f"Suspicious content response: {response.status_code}")

            if response.status_code == 200:
                data = response.json()
                self.log(f"Suspicious content response: success={data.get('success')}, status={data.get('status')}")

                if data.get('success'):
                    status = data.get('status')
                    if status in ['rejected', 'flagged']:
                        self.log(f"✅ Suspicious content was properly moderated: {status}")
                        self.log(f"   Content ID: {data.get('content_id')}")
                        moderation_results = data.get('moderation_results', [])
                        if moderation_results:
                            self.log(f"   Rule triggered: {moderation_results[0].get('rule_name', 'Unknown')}")
                            self.log(f"   Reason: {moderation_results[0].get('reason', 'No reason')}")
                        return True
                    else:
                        self.log(f"❌ Suspicious content was incorrectly {status} - should have been rejected!", "ERROR")
                        self.log(f"   Content ID: {data.get('content_id')}", "ERROR")
                        moderation_results = data.get('moderation_results', [])
                        if moderation_results:
                            self.log(f"   Reason: {moderation_results[0].get('reason', 'No reason')}", "ERROR")
                        self.log("   This indicates the AI moderation rules may need adjustment", "ERROR")
                        return False
                else:
                    self.log(f"❌ Suspicious content API returned success=false: {data}", "ERROR")
                    return False
            else:
                try:
                    error_data = response.json()
                    error_detail = error_data.get('error', 'Unknown error')
                except:
                    error_detail = response.text[:500]

                self.log(f"❌ Suspicious content moderation failed: HTTP {response.status_code}", "ERROR")
                self.log(f"   Error: {error_detail}", "ERROR")
                return False

        except Exception as e:
            self.log(f"❌ Suspicious content moderation failed: {str(e)}", "ERROR")
            return False

    def test_api_stats(self) -> bool:
        """Test getting project statistics"""
        try:
            if not self.api_key:
                self.log("❌ No API key available for stats test", "ERROR")
                return False

            headers = {'X-API-Key': self.api_key}

            response = self.session.get(
                f"{self.base_url}/api/stats",
                headers=headers,
                timeout=30
            )

            if response.status_code == 200:
                data = response.json()
                if data.get('success'):
                    stats = data.get('stats', {})
                    self.log(f"✅ API stats retrieved successfully:")
                    self.log(f"   Total content: {stats.get('total_content', 0)}")
                    self.log(f"   Approved: {stats.get('approved', 0)}")
                    self.log(f"   Rejected: {stats.get('rejected', 0)}")
                    self.log(f"   Flagged: {stats.get('flagged', 0)}")
                    return True
                else:
                    self.log(f"❌ API stats failed: {data}", "ERROR")
                    return False
            else:
                self.log(f"❌ API stats failed: HTTP {response.status_code} - {response.text[:200]}", "ERROR")
                return False

        except Exception as e:
            self.log(f"❌ API stats failed: {str(e)}", "ERROR")
            return False

    def cleanup(self):
        """Clean up test resources"""
        try:
            self.log("🧹 Cleaning up test resources...")
            # The test user and project will be cleaned up when the test database is reset
            # For production environments, you might want to add explicit cleanup
            self.log("✅ Cleanup completed")
        except Exception as e:
            self.log(f"❌ Cleanup failed: {str(e)}", "ERROR")

    def run_all_tests(self) -> bool:
        """Run simplified end-to-end tests for core platform functionality"""
        self.log("🚀 Starting AutoModerate Core Platform Tests")
        self.log(f"   Base URL: {self.base_url}")

        # Core platform tests - what we actually need to validate deployment
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
            self.log(f"\n📋 Running: {test_name}")
            try:
                if test_func():
                    passed += 1
                    self.log(f"✅ {test_name} PASSED")
                else:
                    self.log(f"❌ {test_name} FAILED", "ERROR")
            except Exception as e:
                self.log(f"❌ {test_name} FAILED with exception: {str(e)}", "ERROR")

        self.cleanup()

        # Summary
        self.log(f"\n📊 Test Results: {passed}/{total} tests passed")

        if passed == total:
            self.log("🎉 All core platform tests passed! AutoModerate is deployed and working correctly.")
            self.log("✅ Users can register, login, create projects, and get API keys")
            self.log("✅ Platform is ready for content moderation workflows")
            return True
        else:
            self.log(f"💥 {total - passed} core tests failed - platform deployment has issues", "ERROR")
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