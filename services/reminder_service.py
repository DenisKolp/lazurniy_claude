"""
Reminder service for events and votings
"""
import asyncio
from datetime import datetime, timedelta
from telegram.ext import ContextTypes
from database.crud import EventCRUD, VotingCRUD, UserCRUD
from database.models import VotingStatus
from database.session import async_session_maker
from utils.helpers import format_datetime, is_quiet_hours
from config import config
from services.sheets_service import sheets_service
import logging

logger = logging.getLogger(__name__)


class ReminderService:
    """Service for sending reminders"""

    def __init__(self, bot):
        self.bot = bot

    async def send_event_reminders(self):
        """Send reminders for upcoming events"""
        logger.info("Checking events for reminders...")

        async with async_session_maker() as session:
            events = await EventCRUD.get_for_reminders(session, config.REMINDER_HOURS_BEFORE)

            for event in events:
                await self._send_event_reminder(event)
                await EventCRUD.update(session, event, reminder_sent=True)

        logger.info(f"Sent {len(events)} event reminders")

    async def _send_event_reminder(self, event):
        """Send reminder for a specific event"""
        event_date = format_datetime(event.event_date, "%d.%m.%Y %H:%M")

        message = (
            f"🔔 *Напоминание о событии*\n\n"
            f"*{event.title}*\n\n"
            f"{event.description}\n\n"
            f"📍 Место: {event.location or 'Не указано'}\n"
            f"🕐 Дата и время: {event_date}\n\n"
            f"Событие начнется через {config.REMINDER_HOURS_BEFORE} ч."
        )

        async with async_session_maker() as session:
            verified_users = await UserCRUD.get_all_verified(session)

            for user in verified_users:
                if user.notifications_enabled and not is_quiet_hours():
                    try:
                        await self.bot.send_message(
                            chat_id=user.telegram_id,
                            text=message,
                            parse_mode='Markdown'
                        )
                        await asyncio.sleep(0.1)  # Rate limiting
                    except Exception as e:
                        logger.error(f"Failed to send reminder to {user.telegram_id}: {e}")

    async def send_voting_reminders(self):
        """Send reminders for ending votings"""
        logger.info("Checking votings for reminders...")

        async with async_session_maker() as session:
            active_votings = await VotingCRUD.get_active(session)

            for voting in active_votings:
                time_until_end = voting.ends_at - datetime.utcnow()

                # Send reminder 24 hours before end
                if timedelta(hours=23) < time_until_end < timedelta(hours=25):
                    await self._send_voting_reminder(voting)

        logger.info("Voting reminders checked")

    async def _send_voting_reminder(self, voting):
        """Send reminder for ending voting"""
        ends_at = format_datetime(voting.ends_at, "%d.%m.%Y %H:%M")

        message = (
            f"⏰ *Напоминание о голосовании*\n\n"
            f"*{voting.title}*\n\n"
            f"Голосование завершится: {ends_at}\n\n"
            f"Если вы еще не проголосовали, используйте /voting"
        )

        async with async_session_maker() as session:
            from database.crud import VoteCRUD
            verified_users = await UserCRUD.get_all_verified(session)

            for user in verified_users:
                # Check if user already voted
                existing_vote = await VoteCRUD.get_user_vote(session, user.id, voting.id)

                if not existing_vote and user.notifications_enabled and not is_quiet_hours():
                    try:
                        await self.bot.send_message(
                            chat_id=user.telegram_id,
                            text=message,
                            parse_mode='Markdown'
                        )
                        await asyncio.sleep(0.1)
                    except Exception as e:
                        logger.error(f"Failed to send voting reminder to {user.telegram_id}: {e}")

    async def close_expired_votings(self):
        """Close expired votings and calculate results"""
        logger.info("Checking for expired votings...")

        async with async_session_maker() as session:
            from database.crud import VoteCRUD
            active_votings = await VotingCRUD.get_active(session)

            for voting in active_votings:
                if voting.ends_at <= datetime.utcnow():
                    # Calculate results
                    results = await VoteCRUD.get_voting_results(session, voting.id)
                    total_votes = await VoteCRUD.count_votes(session, voting.id)

                    # Update voting status
                    await VotingCRUD.update(
                        session,
                        voting,
                        status=VotingStatus.COMPLETED,
                        results=results,
                        total_votes=total_votes
                    )

                    # Send results notification
                    await self._send_voting_results(voting, results, total_votes)

                    logger.info(f"Closed voting {voting.id}: {voting.title}")

    async def _send_voting_results(self, voting, results: dict, total_votes: int):
        """Send voting results to all users"""
        import json
        from utils.helpers import format_voting_results

        options = json.loads(voting.options) if isinstance(voting.options, str) else voting.options

        # Export to Google Sheets
        sheets_url = None
        try:
            sheets_url = await sheets_service.export_voting_results(
                voting_id=voting.id,
                voting_title=voting.title,
                voting_description=voting.description or "",
                options=options,
                results=results,
                total_votes=total_votes,
                created_at=voting.created_at,
                ends_at=voting.ends_at
            )
            if sheets_url:
                logger.info(f"Voting results exported to Google Sheets: {sheets_url}")
        except Exception as e:
            logger.error(f"Failed to export to Google Sheets: {e}")

        message = f"📊 *Голосование завершено*\n\n"
        message += f"*{voting.title}*\n\n"
        message += f"Всего голосов: {total_votes}\n\n"
        message += "*Результаты:*\n"

        for i, option in enumerate(options):
            votes = results.get(i, 0)
            percent = (votes / total_votes * 100) if total_votes > 0 else 0
            message += f"{i+1}. {option}: {votes} ({percent:.1f}%)\n"

        # Add Google Sheets link if available
        if sheets_url:
            message += f"\n📄 [Просмотреть детальные результаты]({sheets_url})"

        async with async_session_maker() as session:
            verified_users = await UserCRUD.get_all_verified(session)

            for user in verified_users:
                if user.notifications_enabled and not is_quiet_hours():
                    try:
                        await self.bot.send_message(
                            chat_id=user.telegram_id,
                            text=message,
                            parse_mode='Markdown'
                        )
                        await asyncio.sleep(0.1)
                    except Exception as e:
                        logger.error(f"Failed to send results to {user.telegram_id}: {e}")


async def start_reminder_service(context: ContextTypes.DEFAULT_TYPE):
    """Start reminder service job"""
    reminder_service = ReminderService(context.bot)

    # Run tasks
    await reminder_service.send_event_reminders()
    await reminder_service.send_voting_reminders()
    await reminder_service.close_expired_votings()
