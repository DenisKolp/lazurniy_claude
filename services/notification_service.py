"""
Notification service
"""
import asyncio
from telegram.ext import ContextTypes
from database.crud import NotificationCRUD, UserCRUD
from database.session import async_session_maker
from utils.helpers import is_quiet_hours
import logging

logger = logging.getLogger(__name__)


class NotificationService:
    """Service for managing notifications"""

    def __init__(self, bot):
        self.bot = bot

    async def process_pending_notifications(self):
        """Process and send pending notifications"""
        if is_quiet_hours():
            logger.info("Quiet hours - skipping notifications")
            return

        async with async_session_maker() as session:
            pending = await NotificationCRUD.get_pending(session)

            for notification in pending:
                await self._send_notification(notification)
                await NotificationCRUD.mark_sent(session, notification)

        logger.info(f"Processed {len(pending)} notifications")

    async def _send_notification(self, notification):
        """Send a single notification"""
        async with async_session_maker() as session:
            if notification.user_id:
                # Send to specific user
                try:
                    await self.bot.send_message(
                        chat_id=notification.user_id,
                        text=f"🔔 *{notification.title}*\n\n{notification.message}",
                        parse_mode='Markdown'
                    )
                except Exception as e:
                    logger.error(f"Failed to send notification to {notification.user_id}: {e}")
            else:
                # Send to all association members
                verified_users = await UserCRUD.get_all_verified(session)

                for user in verified_users:
                    if user.notifications_enabled:
                        try:
                            await self.bot.send_message(
                                chat_id=user.telegram_id,
                                text=f"🔔 *{notification.title}*\n\n{notification.message}",
                                parse_mode='Markdown'
                            )
                            await asyncio.sleep(0.1)  # Rate limiting
                        except Exception as e:
                            logger.error(f"Failed to send notification to {user.telegram_id}: {e}")


async def process_notifications_job(context: ContextTypes.DEFAULT_TYPE):
    """Job for processing notifications"""
    notification_service = NotificationService(context.bot)
    await notification_service.process_pending_notifications()
