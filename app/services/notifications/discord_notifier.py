"""Discord webhook notification service for content moderation alerts."""

import logging
import os
from datetime import datetime
from typing import Any, Dict, Optional

import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

logger = logging.getLogger(__name__)


class DiscordNotifier:
    """
    Sends notifications to Discord via webhooks when content is flagged or rejected.

    Features:
    - Rich embed formatting
    - Automatic retries with exponential backoff
    - Error handling and logging
    - Support for both global and per-project webhooks
    """

    # Discord embed color codes
    COLOR_FLAGGED = 0xFFA500  # Orange
    COLOR_REJECTED = 0xFF0000  # Red
    COLOR_INFO = 0x3498DB  # Blue

    def __init__(self, webhook_url: Optional[str] = None):
        """
        Initialize Discord notifier.

        Args:
            webhook_url: Discord webhook URL. If None, uses DISCORD_WEBHOOK_URL from env.
        """
        self.webhook_url = webhook_url or os.getenv('DISCORD_WEBHOOK_URL')

        # Configure session with retry logic
        self.session = requests.Session()
        retry_strategy = Retry(
            total=3,
            backoff_factor=1,
            status_forcelist=[429, 500, 502, 503, 504],
            allowed_methods=["POST"]
        )
        adapter = HTTPAdapter(max_retries=retry_strategy)
        self.session.mount("https://", adapter)
        self.session.mount("http://", adapter)

    def is_configured(self) -> bool:
        """Check if webhook URL is configured."""
        return bool(self.webhook_url)

    def send_flagged_content_notification(
        self,
        content_id: str,
        project_id: str,
        project_name: str,
        status: str,
        confidence: float,
        reason: str,
        moderator_type: str,
        metadata: Optional[Dict[str, Any]] = None,
        base_url: str = "http://localhost:6217"
    ) -> bool:
        """
        Send notification for flagged or rejected content.

        Args:
            content_id: UUID of the content
            project_id: UUID of the project
            project_name: Name of the project
            status: Content status (flagged, rejected, etc.)
            confidence: Confidence score (0-1)
            reason: Moderation reason
            moderator_type: Type of moderator (rule, ai, manual)
            metadata: Additional metadata (e.g., user_id, content_type)
            base_url: Base URL for web UI links

        Returns:
            True if notification sent successfully, False otherwise
        """
        if not self.is_configured():
            logger.warning("Discord webhook not configured, skipping notification")
            return False

        try:
            # Determine emoji and color based on status
            if status == "rejected":
                emoji = "🚫"
                color = self.COLOR_REJECTED
            elif status == "flagged":
                emoji = "🚩"
                color = self.COLOR_FLAGGED
            else:
                emoji = "ℹ️"
                color = self.COLOR_INFO

            # Build content link to manual review page (project-specific)
            content_url = f"{base_url}/projects/{project_id}/manual-review/{content_id}"

            # Extract user ID from metadata if available
            user_id = "N/A"
            user_link = None
            api_user_id = None

            if metadata:
                user_id = metadata.get('user_id', 'N/A')
                api_user_id = metadata.get('api_user_id')

                # Create link to API user page if we have the ID
                if api_user_id:
                    user_link = f"{base_url}/api-users/{api_user_id}"

            # Build embed fields
            fields = [
                {
                    "name": "Project",
                    "value": project_name,
                    "inline": True
                },
                {
                    "name": "Content ID",
                    "value": f"`{content_id[:8]}...`",
                    "inline": True
                },
                {
                    "name": "User ID",
                    "value": f"`{user_id}`" if user_id != "N/A" else "N/A",
                    "inline": True
                },
                {
                    "name": "Status",
                    "value": status.title(),
                    "inline": True
                },
                {
                    "name": "Confidence",
                    "value": f"{confidence:.2%}",
                    "inline": True
                },
                {
                    "name": "Moderator",
                    "value": moderator_type.title(),
                    "inline": True
                }
            ]

            # Add links section
            links = [f"[View Content]({content_url})"]
            if user_link:
                links.append(f"[View User Profile]({user_link})")

            fields.append({
                "name": "Links",
                "value": " • ".join(links),
                "inline": False
            })

            # Build embed
            embed = {
                "title": f"{emoji} Content {status.title()} for Review",
                "description": reason,
                "color": color,
                "fields": fields,
                "timestamp": datetime.utcnow().isoformat(),
                "footer": {
                    "text": "AutoModerate"
                }
            }

            # Send webhook
            payload = {
                "embeds": [embed]
            }

            response = self.session.post(
                self.webhook_url,
                json=payload,
                timeout=10
            )
            response.raise_for_status()

            logger.info(f"Discord notification sent for content {content_id}")
            return True

        except requests.exceptions.RequestException as e:
            logger.error(f"Failed to send Discord notification: {e}")
            return False
        except Exception as e:
            logger.error(f"Unexpected error sending Discord notification: {e}")
            return False

    def send_test_notification(self, project_name: str = "Test Project") -> bool:
        """
        Send a test notification to verify webhook configuration.

        Args:
            project_name: Name to use in test notification

        Returns:
            True if test notification sent successfully, False otherwise
        """
        if not self.is_configured():
            return False

        try:
            embed = {
                "title": "✅ Discord Webhook Test",
                "description": "Your Discord webhook is configured correctly!",
                "color": 0x00FF00,  # Green
                "fields": [
                    {
                        "name": "Project",
                        "value": project_name,
                        "inline": True
                    },
                    {
                        "name": "Status",
                        "value": "Connected",
                        "inline": True
                    }
                ],
                "timestamp": datetime.utcnow().isoformat(),
                "footer": {
                    "text": "AutoModerate"
                }
            }

            payload = {"embeds": [embed]}
            response = self.session.post(
                self.webhook_url,
                json=payload,
                timeout=10
            )
            response.raise_for_status()

            logger.info("Discord test notification sent successfully")
            return True

        except requests.exceptions.RequestException as e:
            logger.error(f"Failed to send Discord test notification: {e}")
            return False

    def close(self):
        """Close the session."""
        self.session.close()
