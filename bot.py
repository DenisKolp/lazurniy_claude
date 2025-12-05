"""
Main bot file - Lazurny Village Association Bot
"""
import asyncio
import logging
from telegram.ext import Application, CommandHandler
from config import config
from database.session import init_db
from handlers import (
    register_start_handlers,
    register_voting_handlers,
    register_events_handlers,
    register_tickets_handlers,
    register_admin_handlers
)
from services.reminder_service import start_reminder_service
from services.notification_service import process_notifications_job

# Configure logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO if config.DEBUG else logging.WARNING
)
logger = logging.getLogger(__name__)


async def post_init(application: Application):
    """Post initialization callback"""
    logger.info("Initializing database...")
    await init_db()
    logger.info("Database initialized successfully")

    # Set up admin users in database
    from database.session import async_session_maker
    from database.crud import UserCRUD

    async with async_session_maker() as session:
        for admin_id in config.ADMIN_IDS:
            user = await UserCRUD.get_by_telegram_id(session, admin_id)
            if user:
                await UserCRUD.update(session, user, is_admin=True)
                logger.info(f"Updated admin status for user {admin_id}")


async def error_handler(update, context):
    """Handle errors"""
    logger.error(f"Update {update} caused error {context.error}", exc_info=context.error)


def main():
    """Start the bot"""
    logger.info("Starting Lazurny Bot...")

    # Validate configuration
    try:
        config.validate()
    except ValueError as e:
        logger.error(f"Configuration error: {e}")
        return

    # Create application
    application = (
        Application.builder()
        .token(config.BOT_TOKEN)
        .post_init(post_init)
        .read_timeout(30)
        .write_timeout(30)
        .connect_timeout(30)
        .build()
    )

    # Register handlers
    logger.info("Registering handlers...")
    register_voting_handlers(application)
    register_events_handlers(application)
    register_tickets_handlers(application)
    register_admin_handlers(application)
    # Register start handlers last (contains catch-all handler)
    register_start_handlers(application)

    # Register error handler
    application.add_error_handler(error_handler)

    # Schedule jobs
    logger.info("Setting up scheduled jobs...")
    job_queue = application.job_queue

    # Check reminders every hour
    job_queue.run_repeating(
        start_reminder_service,
        interval=3600,  # 1 hour
        first=10  # Start after 10 seconds
    )

    # Process notifications every 5 minutes
    job_queue.run_repeating(
        process_notifications_job,
        interval=300,  # 5 minutes
        first=10
    )

    logger.info("Bot started successfully!")
    logger.info(f"Debug mode: {config.DEBUG}")
    logger.info(f"Admins: {config.ADMIN_IDS}")

    # Start polling
    application.run_polling(allowed_updates=["message", "callback_query", "chat_member"])


if __name__ == "__main__":
    main()
