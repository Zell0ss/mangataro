"""
Notification Service

Sends notifications for new chapters via Telegram or Discord webhooks.
"""

import os
import httpx
from typing import List, Dict, Optional
from datetime import datetime

# Import centralized logging configuration
import api.logging_config
from api.logging_config import get_logger

# Get API-specific logger for notifications
logger = get_logger("api")


def _format_chapter_range(numbers: List[str]) -> str:
    """
    Format a list of chapter number strings into a compact range string.

    Examples:
        ["200", "201", "202"] → "200-202"
        ["200", "202", "203"] → "200, 202-203"
        ["200"]               → "200"
    """
    # Parse to float to handle decimals like "42.5", then sort
    parsed = sorted(set(numbers), key=lambda x: float(x))

    groups = []
    start = parsed[0]
    prev = parsed[0]

    for current in parsed[1:]:
        # Consider consecutive if difference is exactly 1 (integers only)
        try:
            if float(current) - float(prev) == 1 and float(prev) == int(float(prev)):
                prev = current
                continue
        except ValueError:
            pass
        # Gap found — close current group
        groups.append((start, prev))
        start = current
        prev = current

    groups.append((start, prev))

    parts = []
    for s, e in groups:
        parts.append(s if s == e else f"{s}-{e}")

    return ", ".join(parts)


class NotificationService:
    """Handles notifications for new chapters."""

    def __init__(self):
        self.notification_type = os.getenv("NOTIFICATION_TYPE", "discord")
        self.discord_webhook_url = os.getenv("DISCORD_WEBHOOK_URL")
        self.telegram_bot_token = os.getenv("TELEGRAM_BOT_TOKEN")
        self.telegram_chat_id = os.getenv("TELEGRAM_CHAT_ID")

    async def notify_new_chapters(self, chapters: List[Dict]) -> bool:
        """
        Send notification for new chapters.

        Args:
            chapters: List of chapter dicts with manga_title, chapter_number, url, scanlator_name

        Returns:
            True if notification sent successfully, False otherwise
        """
        if not chapters:
            logger.info("No new chapters to notify")
            return True

        if self.notification_type == "telegram":
            return await self._notify_telegram(chapters)
        elif self.notification_type == "discord":
            return await self._notify_discord(chapters)
        else:
            logger.warning(f"Notification type '{self.notification_type}' not implemented")
            return False

    async def _notify_telegram(self, chapters: List[Dict]) -> bool:
        """Send Telegram notification grouping chapters by manga + scanlator."""
        if not self.telegram_bot_token or not self.telegram_chat_id:
            logger.warning("Telegram credentials not configured, skipping notification")
            return False

        # Group chapters by (manga_title, scanlator_name)
        groups: Dict[tuple, List[str]] = {}
        for ch in chapters:
            key = (ch["manga_title"], ch.get("scanlator_name", ""))
            groups.setdefault(key, []).append(ch["chapter_number"])

        lines = []
        for (manga_title, scanlator_name), numbers in sorted(groups.items()):
            chapter_str = _format_chapter_range(numbers)
            lines.append(f"• <b>{manga_title}</b>: {chapter_str} ({scanlator_name})")

        total = len(chapters)
        header = f"📚 <b>{total} nuevo{'s' if total != 1 else ''} capítulo{'s' if total != 1 else ''}</b>\n"
        text = header + "\n".join(lines)

        url = f"https://api.telegram.org/bot{self.telegram_bot_token}/sendMessage"
        payload = {
            "chat_id": self.telegram_chat_id,
            "text": text,
            "parse_mode": "HTML",
            "disable_web_page_preview": True,
        }

        try:
            async with httpx.AsyncClient() as client:
                response = await client.post(url, json=payload, timeout=10.0)
                response.raise_for_status()
                logger.info(f"Telegram notification sent for {total} chapters")
                return True
        except httpx.HTTPError as e:
            logger.error(f"Failed to send Telegram notification: {e}")
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
