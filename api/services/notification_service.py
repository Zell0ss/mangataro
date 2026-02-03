"""
Notification Service

Sends notifications for new chapters via Discord webhooks or email.
"""

import os
import httpx
from typing import List, Dict, Optional
from loguru import logger
from datetime import datetime


class NotificationService:
    """Handles notifications for new chapters."""

    def __init__(self):
        self.notification_type = os.getenv("NOTIFICATION_TYPE", "discord")
        self.discord_webhook_url = os.getenv("DISCORD_WEBHOOK_URL")

    async def notify_new_chapters(self, chapters: List[Dict]) -> bool:
        """
        Send notification for new chapters.

        Args:
            chapters: List of chapter dictionaries with manga_title, chapter_number, url

        Returns:
            True if notification sent successfully, False otherwise
        """
        if not chapters:
            logger.info("No new chapters to notify")
            return True

        if self.notification_type == "discord":
            return await self._notify_discord(chapters)
        else:
            logger.warning(f"Notification type '{self.notification_type}' not implemented")
            return False

    async def _notify_discord(self, chapters: List[Dict]) -> bool:
        """Send Discord webhook notification."""
        if not self.discord_webhook_url:
            logger.warning("Discord webhook URL not configured, skipping notification")
            return False

        # Build embed message
        embeds = []

        for chapter in chapters[:10]:  # Limit to 10 chapters per notification
            embed = {
                "title": f"{chapter['manga_title']} - Chapter {chapter['chapter_number']}",
                "url": chapter.get("url", ""),
                "description": chapter.get("title", "New chapter available"),
                "color": 0x00ff00,  # Green
                "timestamp": chapter.get("detected_date", datetime.utcnow()).isoformat(),
                "footer": {
                    "text": f"Scanlator: {chapter.get('scanlator_name', 'Unknown')}"
                }
            }
            embeds.append(embed)

        # Add summary if more than 10 chapters
        if len(chapters) > 10:
            embeds.append({
                "title": "📚 And more...",
                "description": f"{len(chapters) - 10} additional chapters detected",
                "color": 0x0099ff
            })

        payload = {
            "content": f"🆕 **{len(chapters)} new chapter(s) detected!**",
            "embeds": embeds
        }

        try:
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    self.discord_webhook_url,
                    json=payload,
                    timeout=10.0
                )
                response.raise_for_status()
                logger.info(f"Discord notification sent for {len(chapters)} chapters")
                return True
        except httpx.HTTPError as e:
            logger.error(f"Failed to send Discord notification: {e}")
            return False


# Singleton instance
_notification_service = NotificationService()


def get_notification_service() -> NotificationService:
    """Get the notification service singleton."""
    return _notification_service
