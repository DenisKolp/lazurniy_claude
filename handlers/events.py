"""
Events calendar handlers
"""
from datetime import datetime
import pytz
from telegram import Update, InlineKeyboardMarkup, InlineKeyboardButton
from telegram.ext import (
    ContextTypes, CommandHandler, MessageHandler,
    filters, ConversationHandler, CallbackQueryHandler
)
from database.crud import UserCRUD, EventCRUD
from database.models import UserStatus
from database.session import async_session_maker
from utils.validators import validate_title, validate_description
from utils.helpers import format_datetime
from dateutil import parser
from config import config


# Conversation states
EVENT_TITLE, EVENT_DESCRIPTION, EVENT_DATE, EVENT_LOCATION = range(4)


async def events_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Show events menu"""
    async with async_session_maker() as session:
        user = await UserCRUD.get_by_telegram_id(session, update.effective_user.id)

        if not user or user.status != UserStatus.VERIFIED:
            await update.message.reply_text(
                "❌ Доступ запрещен. Пройдите верификацию (/verify)."
            )
            return

        upcoming_events = await EventCRUD.get_upcoming(session, limit=5)

        text = "📅 *Календарь событий*\n\n"
        if upcoming_events:
            text += "Ближайшие события:\n\n"
            for event in upcoming_events:
                event_date = format_datetime(event.event_date, "%d.%m.%Y %H:%M")
                text += f"• *{event.title}*\n"
                text += f"  📍 {event.location or 'Место не указано'}\n"
                text += f"  🕐 {event_date}\n\n"
        else:
            text += "Нет запланированных событий.\n\n"

        keyboard = [
            [InlineKeyboardButton("📋 Все события", callback_data="events_list")],
        ]

        if user.is_admin:
            keyboard.append([InlineKeyboardButton("➕ Создать событие", callback_data="event_create")])

        reply_markup = InlineKeyboardMarkup(keyboard)
        await update.message.reply_text(text, reply_markup=reply_markup, parse_mode='Markdown')


async def events_list_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Show list of upcoming events"""
    query = update.callback_query
    await query.answer()

    async with async_session_maker() as session:
        upcoming_events = await EventCRUD.get_upcoming(session, limit=20)

        if not upcoming_events:
            await query.edit_message_text("Нет запланированных событий.")
            return

        keyboard = []
        for event in upcoming_events:
            event_date = format_datetime(event.event_date, "%d.%m %H:%M")
            keyboard.append([
                InlineKeyboardButton(
                    f"{event_date} - {event.title[:30]}",
                    callback_data=f"event_view_{event.id}"
                )
            ])
        keyboard.append([InlineKeyboardButton("◀️ Назад", callback_data="events_menu")])

        reply_markup = InlineKeyboardMarkup(keyboard)
        await query.edit_message_text(
            "Выберите событие:",
            reply_markup=reply_markup
        )


async def event_view_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """View event details"""
    query = update.callback_query
    await query.answer()

    event_id = int(query.data.split("_")[2])

    async with async_session_maker() as session:
        event = await EventCRUD.get_by_id(session, event_id)
        if not event:
            await query.edit_message_text("❌ Событие не найдено.")
            return

        user = await UserCRUD.get_by_telegram_id(session, query.from_user.id)

        event_date = format_datetime(event.event_date, "%d.%m.%Y %H:%M")

        text = f"📅 *{event.title}*\n\n"
        text += f"{event.description}\n\n"
        text += f"📍 Место: {event.location or 'Не указано'}\n"
        text += f"🕐 Дата и время: {event_date}\n"

        keyboard = []
        if user.is_admin:
            keyboard.append([
                InlineKeyboardButton("✏️ Редактировать", callback_data=f"event_edit_{event.id}"),
                InlineKeyboardButton("🗑️ Удалить", callback_data=f"event_delete_{event.id}")
            ])
        keyboard.append([InlineKeyboardButton("◀️ Назад к списку", callback_data="events_list")])

        reply_markup = InlineKeyboardMarkup(keyboard)
        await query.edit_message_text(text, reply_markup=reply_markup, parse_mode='Markdown')


async def event_create_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Start creating a new event"""
    query = update.callback_query
    await query.answer()

    async with async_session_maker() as session:
        user = await UserCRUD.get_by_telegram_id(session, query.from_user.id)
        if not user or not user.is_admin:
            await query.answer("❌ Доступ запрещен.", show_alert=True)
            return

    await query.edit_message_text(
        "📝 *Создание события*\n\n"
        "Шаг 1/4: Введите название события:",
        parse_mode='Markdown'
    )
    return EVENT_TITLE


async def event_receive_title(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Receive event title"""
    title = update.message.text.strip()

    if not validate_title(title):
        await update.message.reply_text(
            "❌ Название должно быть от 5 до 500 символов. Попробуйте еще раз:"
        )
        return EVENT_TITLE

    context.user_data['event_title'] = title
    await update.message.reply_text(
        "✅ Название сохранено!\n\n"
        "Шаг 2/4: Введите описание события:"
    )
    return EVENT_DESCRIPTION


async def event_receive_description(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Receive event description"""
    description = update.message.text.strip()

    if not validate_description(description):
        await update.message.reply_text(
            "❌ Описание должно быть от 10 до 4000 символов. Попробуйте еще раз:"
        )
        return EVENT_DESCRIPTION

    context.user_data['event_description'] = description
    await update.message.reply_text(
        "✅ Описание сохранено!\n\n"
        "Шаг 3/4: Введите дату и время события (формат: ДД.ММ.ГГГГ ЧЧ:ММ):\n\n"
        "Например: 25.12.2025 18:00"
    )
    return EVENT_DATE


async def event_receive_date(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Receive event date"""
    date_text = update.message.text.strip()

    try:
        # Parse date as naive datetime
        event_date = parser.parse(date_text, dayfirst=True)

        # Add timezone from config
        tz = pytz.timezone(config.TIMEZONE)

        # If datetime is naive, localize it
        if event_date.tzinfo is None:
            event_date = tz.localize(event_date)

        # Convert to UTC for storage
        event_date_utc = event_date.astimezone(pytz.UTC).replace(tzinfo=None)

        # Check if date is in the future (compare in local timezone)
        now_local = datetime.now(tz)
        if event_date < now_local:
            await update.message.reply_text(
                "❌ Дата должна быть в будущем. Попробуйте еще раз:"
            )
            return EVENT_DATE
    except Exception as e:
        await update.message.reply_text(
            "❌ Неверный формат даты. Используйте формат: ДД.ММ.ГГГГ ЧЧ:ММ\n"
            "Например: 25.12.2025 18:00"
        )
        return EVENT_DATE

    context.user_data['event_date'] = event_date_utc
    await update.message.reply_text(
        "✅ Дата сохранена!\n\n"
        "Шаг 4/4: Введите место проведения (или напишите 'пропустить'):"
    )
    return EVENT_LOCATION


async def event_receive_location(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Receive event location and create event"""
    location_text = update.message.text.strip()
    location = None if location_text.lower() == 'пропустить' else location_text

    async with async_session_maker() as session:
        user = await UserCRUD.get_by_telegram_id(session, update.effective_user.id)

        event = await EventCRUD.create(
            session,
            title=context.user_data['event_title'],
            description=context.user_data['event_description'],
            event_date=context.user_data['event_date'],
            location=location,
            creator_id=user.id
        )

    event_date_str = format_datetime(event.event_date, "%d.%m.%Y %H:%M")

    await update.message.reply_text(
        f"✅ Событие создано!\n\n"
        f"Название: {event.title}\n"
        f"Дата: {event_date_str}\n"
        f"Место: {event.location or 'Не указано'}\n\n"
        "Событие добавлено в календарь."
    )

    # Notify all association members
    async with async_session_maker() as session:
        verified_users = await UserCRUD.get_all_verified(session)
        for verified_user in verified_users:
            if verified_user.notifications_enabled and verified_user.telegram_id != user.telegram_id:
                try:
                    await context.bot.send_message(
                        chat_id=verified_user.telegram_id,
                        text=f"📅 Новое событие в календаре!\n\n"
                             f"*{event.title}*\n\n"
                             f"📍 {event.location or 'Место не указано'}\n"
                             f"🕐 {event_date_str}",
                        parse_mode='Markdown'
                    )
                except Exception:
                    pass

    context.user_data.clear()
    return ConversationHandler.END


async def event_delete_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Delete event"""
    query = update.callback_query
    await query.answer()

    event_id = int(query.data.split("_")[2])

    async with async_session_maker() as session:
        user = await UserCRUD.get_by_telegram_id(session, query.from_user.id)
        if not user or not user.is_admin:
            await query.answer("❌ Доступ запрещен.", show_alert=True)
            return

        event = await EventCRUD.get_by_id(session, event_id)
        if not event:
            await query.answer("❌ Событие не найдено.", show_alert=True)
            return

        await EventCRUD.delete(session, event)

    await query.answer("✅ Событие удалено.", show_alert=True)
    await events_list_callback(update, context)


def register_events_handlers(application):
    """Register events handlers"""
    # Events menu
    application.add_handler(MessageHandler(
        filters.Regex("^📅 События$"),
        events_menu
    ))

    # Callbacks
    application.add_handler(CallbackQueryHandler(events_menu, pattern="^events_menu$"))
    application.add_handler(CallbackQueryHandler(events_list_callback, pattern="^events_list$"))
    application.add_handler(CallbackQueryHandler(event_view_callback, pattern="^event_view_"))
    application.add_handler(CallbackQueryHandler(event_delete_callback, pattern="^event_delete_"))

    # Create event conversation
    create_event_conv = ConversationHandler(
        entry_points=[CallbackQueryHandler(event_create_start, pattern="^event_create$")],
        states={
            EVENT_TITLE: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, event_receive_title)
            ],
            EVENT_DESCRIPTION: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, event_receive_description)
            ],
            EVENT_DATE: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, event_receive_date)
            ],
            EVENT_LOCATION: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, event_receive_location)
            ],
        },
        fallbacks=[],
        allow_reentry=True,
        per_chat=True
    )
    application.add_handler(create_event_conv)
