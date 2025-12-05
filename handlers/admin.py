"""
Admin panel handlers
"""
from datetime import datetime
import logging
from telegram import Update, InlineKeyboardMarkup, InlineKeyboardButton
from telegram.ext import (
    ContextTypes, CommandHandler, MessageHandler,
    filters, ConversationHandler, CallbackQueryHandler
)

logger = logging.getLogger(__name__)
from database.crud import UserCRUD, VotingCRUD, EventCRUD, TicketCRUD
from database.models import UserStatus, TicketStatus, VotingStatus
from database.session import async_session_maker
from utils.helpers import format_datetime, get_user_display_name
from services.sheets_service import sheets_service
from config import config
import json
from datetime import timedelta


# Conversation states
EMERGENCY_MESSAGE, TICKET_RESPONSE, REJECT_REASON = range(3)


async def safe_answer_query(query):
    """Safely answer callback query, ignoring timeout errors"""
    try:
        await safe_answer_query(query)
    except Exception:
        pass  # Query too old or other error


async def admin_panel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Show admin panel"""
    async with async_session_maker() as session:
        user = await UserCRUD.get_by_telegram_id(session, update.effective_user.id)

        if not user or not user.is_admin:
            await update.message.reply_text("❌ Доступ запрещен.")
            return

        # Get statistics
        pending_users = await UserCRUD.get_pending_verification(session)
        verified_users = await UserCRUD.get_all_verified(session)
        active_votings = await VotingCRUD.get_active(session)
        upcoming_events = await EventCRUD.get_upcoming(session, limit=5)
        open_tickets = await TicketCRUD.get_open_tickets(session)

        text = "👨‍💼 *Админ-панель*\n\n"
        text += f"👥 Пользователей:\n"
        text += f"  • Членов ассоциации: {len(verified_users)}\n"
        text += f"  • На проверке: {len(pending_users)}\n\n"
        text += f"🗳️ Активных голосований: {len(active_votings)}\n"
        text += f"📅 Предстоящих событий: {len(upcoming_events)}\n"
        text += f"📝 Открытых обращений: {len(open_tickets)}\n"

        keyboard = [
            [
                InlineKeyboardButton(f"👥 Пользователи ({len(pending_users)})", callback_data="admin_users"),
                InlineKeyboardButton("🗳️ Голосования", callback_data="admin_votings")
            ],
            [
                InlineKeyboardButton(f"📝 Обращение в ИГ ({len(open_tickets)})", callback_data="admin_tickets"),
                InlineKeyboardButton("📅 События", callback_data="admin_events")
            ],
            [
                InlineKeyboardButton("📢 Оповещение", callback_data="admin_emergency")
            ],
            [
                InlineKeyboardButton("📊 Статистика", callback_data="admin_stats")
            ]
        ]

        reply_markup = InlineKeyboardMarkup(keyboard)
        await update.message.reply_text(text, reply_markup=reply_markup, parse_mode='Markdown')


async def admin_users_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Show users management"""
    query = update.callback_query
    await safe_answer_query(query)

    async with async_session_maker() as session:
        pending_users = await UserCRUD.get_pending_verification(session)

        keyboard = [
            [
                InlineKeyboardButton("📋 На проверке", callback_data="admin_users_pending"),
                InlineKeyboardButton("✅ Члены ассоциации", callback_data="admin_users_verified")
            ],
            [InlineKeyboardButton("◀️ Назад", callback_data="admin_back")]
        ]

        reply_markup = InlineKeyboardMarkup(keyboard)
        await query.edit_message_text(
            f"👥 *Управление пользователями*\n\n"
            f"На проверке: {len(pending_users)}",
            reply_markup=reply_markup,
            parse_mode='Markdown'
        )


async def admin_users_pending_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Show pending users list"""
    query = update.callback_query
    await safe_answer_query(query)

    async with async_session_maker() as session:
        pending_users = await UserCRUD.get_pending_verification(session)

        if not pending_users:
            await query.edit_message_text(
                "✅ Нет пользователей на проверке.",
                reply_markup=InlineKeyboardMarkup([[
                    InlineKeyboardButton("◀️ Назад", callback_data="admin_users")
                ]])
            )
            return

        keyboard = []
        for user in pending_users:
            display_name = get_user_display_name(user)
            keyboard.append([
                InlineKeyboardButton(
                    f"👤 {display_name}",
                    callback_data=f"admin_user_pending_{user.id}"
                )
            ])
        keyboard.append([InlineKeyboardButton("◀️ Назад", callback_data="admin_users")])

        reply_markup = InlineKeyboardMarkup(keyboard)
        await query.edit_message_text(
            "📋 Пользователи на проверке:",
            reply_markup=reply_markup
        )


async def admin_users_verified_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Show association members list"""
    query = update.callback_query
    await safe_answer_query(query)

    async with async_session_maker() as session:
        verified_users = await UserCRUD.get_all_verified(session)

        if not verified_users:
            await query.edit_message_text(
                "Нет членов ассоциации.",
                reply_markup=InlineKeyboardMarkup([[
                    InlineKeyboardButton("◀️ Назад", callback_data="admin_users")
                ]])
            )
            return

        keyboard = []
        for user in verified_users:
            display_name = get_user_display_name(user)
            keyboard.append([
                InlineKeyboardButton(
                    f"✅ {display_name}",
                    callback_data=f"admin_user_verified_{user.id}"
                )
            ])
        keyboard.append([InlineKeyboardButton("◀️ Назад", callback_data="admin_users")])

        reply_markup = InlineKeyboardMarkup(keyboard)
        await query.edit_message_text(
            f"✅ Члены ассоциации ({len(verified_users)}):",
            reply_markup=reply_markup
        )


async def admin_user_view_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """View user verification details"""
    query = update.callback_query
    await safe_answer_query(query)

    # Parse callback data: admin_user_pending_123 or admin_user_verified_123
    parts = query.data.split("_")
    user_status_type = parts[2]  # "pending" or "verified"
    user_id = int(parts[3])

    async with async_session_maker() as session:
        user = await UserCRUD.get_by_id(session, user_id)
        if not user:
            await query.answer("❌ Пользователь не найден.", show_alert=True)
            return

        display_name = get_user_display_name(user)
        created = format_datetime(user.created_at, "%d.%m.%Y %H:%M")

        text = f"👤 {display_name}\n\n"
        text += f"ФИО: {user.full_name or 'Не указано'}\n"
        text += f"Username: @{user.username or 'N/A'}\n"
        text += f"Telegram ID: {user.telegram_id}\n"
        text += f"Телефон: {user.phone_number or 'Не указан'}\n"
        text += f"Адрес: {user.address or 'Не указан'}\n"
        text += f"Дата регистрации: {created}\n"

        if user_status_type == "pending":
            # Buttons for pending users
            keyboard = [
                [
                    InlineKeyboardButton("✅ Одобрить", callback_data=f"admin_approve_{user.id}"),
                    InlineKeyboardButton("❌ Отклонить", callback_data=f"admin_reject_{user.id}")
                ],
                [InlineKeyboardButton("◀️ Назад", callback_data="admin_users_pending")]
            ]
        else:
            # Buttons for association members
            verified_date = format_datetime(user.verified_at, "%d.%m.%Y %H:%M") if user.verified_at else "Неизвестно"
            text += f"Дата верификации: {verified_date}\n"

            keyboard = [
                [InlineKeyboardButton("🗑️ Удалить верификацию", callback_data=f"admin_revoke_{user.id}")],
                [InlineKeyboardButton("◀️ Назад", callback_data="admin_users_verified")]
            ]

        reply_markup = InlineKeyboardMarkup(keyboard)

        # Send documents first if available
        if user.verification_documents:
            try:
                docs = json.loads(user.verification_documents)
                for doc_id in docs:
                    await context.bot.send_document(chat_id=query.message.chat_id, document=doc_id)
            except Exception:
                pass

        await query.edit_message_text(text, reply_markup=reply_markup)


async def admin_approve_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Approve user verification"""
    query = update.callback_query
    try:
        await safe_answer_query(query)
    except Exception:
        pass  # Query too old

    user_id = int(query.data.split("_")[2])

    async with async_session_maker() as session:
        user = await UserCRUD.get_by_id(session, user_id)
        if not user:
            await query.answer("❌ Пользователь не найден.", show_alert=True)
            return

        await UserCRUD.update(
            session,
            user,
            status=UserStatus.VERIFIED,
            verified_at=datetime.utcnow()
        )

        # Export updated registry to Google Sheets
        try:
            verified_users = await UserCRUD.get_all_verified(session)
            members_data = []
            for member in verified_users:
                members_data.append({
                    'full_name': member.full_name,
                    'username': member.username,
                    'phone_number': member.phone_number,
                    'address': member.address,
                    'verified_at': format_datetime(member.verified_at, '%d.%m.%Y %H:%M') if member.verified_at else 'Не указана'
                })

            registry_url = await sheets_service.export_members_registry(members_data)
            if registry_url:
                logger.info(f"Registry exported to Google Sheets: {registry_url}")
        except Exception as e:
            logger.error(f"Failed to export registry: {e}")

    # Notify user
    try:
        from telegram import KeyboardButton, ReplyKeyboardMarkup
        keyboard = [
            [KeyboardButton("🏠 Старт")]
        ]
        reply_markup = ReplyKeyboardMarkup(keyboard, resize_keyboard=True)

        await context.bot.send_message(
            chat_id=user.telegram_id,
            text="✅ Поздравляем! Ваша заявка одобрена.\n\n"
                 "Теперь вы можете пользоваться всеми функциями бота.\n"
                 "Нажмите кнопку ниже для доступа к меню.",
            reply_markup=reply_markup
        )
    except Exception:
        pass

    await query.answer("✅ Пользователь стал членом ассоциации.", show_alert=True)
    await admin_users_pending_callback(update, context)


async def admin_reject_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Reject user verification - start"""
    query = update.callback_query
    await safe_answer_query(query)

    user_id = int(query.data.split("_")[2])
    context.user_data['reject_user_id'] = user_id

    await query.edit_message_text(
        "❌ Введите причину отклонения:"
    )
    return REJECT_REASON


async def admin_reject_reason(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Process rejection reason"""
    reason = update.message.text
    user_id = context.user_data.get('reject_user_id')

    if not user_id:
        await update.message.reply_text("❌ Ошибка: пользователь не найден.")
        return ConversationHandler.END

    async with async_session_maker() as session:
        user = await UserCRUD.get_by_id(session, user_id)
        if not user:
            await update.message.reply_text("❌ Пользователь не найден.")
            return ConversationHandler.END

        # Update user status
        await UserCRUD.update(
            session,
            user,
            status=UserStatus.REJECTED,
            rejected_reason=reason
        )

        # Notify user
        try:
            await context.bot.send_message(
                chat_id=user.telegram_id,
                text=f"❌ Ваша заявка на верификацию отклонена.\n\nПричина: {reason}"
            )
        except Exception as e:
            pass  # User might have blocked the bot

        await update.message.reply_text(
            f"✅ Пользователь {get_user_display_name(user)} отклонен.\n"
            f"Причина: {reason}"
        )

    # Clear user data
    context.user_data.pop('reject_user_id', None)
    return ConversationHandler.END


async def admin_revoke_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Revoke user verification"""
    query = update.callback_query
    await safe_answer_query(query)

    user_id = int(query.data.split("_")[2])

    async with async_session_maker() as session:
        user = await UserCRUD.get_by_id(session, user_id)
        if not user:
            await query.answer("❌ Пользователь не найден.", show_alert=True)
            return

        # Update user status back to pending
        await UserCRUD.update(
            session,
            user,
            status=UserStatus.PENDING,
            verified_at=None
        )

    # Notify user
    try:
        await context.bot.send_message(
            chat_id=user.telegram_id,
            text="⚠️ Ваша верификация была отозвана администратором.\n\n"
                 "Для получения доступа к функциям бота необходимо пройти верификацию повторно."
        )
    except Exception:
        pass  # User might have blocked the bot

    await query.answer("✅ Верификация пользователя удалена.", show_alert=True)
    await admin_users_verified_callback(update, context)


async def admin_tickets_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Show open tickets"""
    query = update.callback_query
    await safe_answer_query(query)

    async with async_session_maker() as session:
        open_tickets = await TicketCRUD.get_open_tickets(session)

        if not open_tickets:
            await query.edit_message_text(
                "✅ Нет открытых обращений.",
                reply_markup=InlineKeyboardMarkup([[
                    InlineKeyboardButton("◀️ Назад", callback_data="admin_back")
                ]])
            )
            return

        keyboard = []
        for ticket in open_tickets:
            status_emoji = {
                TicketStatus.NEW: "🆕",
                TicketStatus.IN_PROGRESS: "⏳"
            }.get(ticket.status, "❓")

            keyboard.append([
                InlineKeyboardButton(
                    f"{status_emoji} #{ticket.id}: {ticket.title[:30]}",
                    callback_data=f"admin_ticket_{ticket.id}"
                )
            ])
        keyboard.append([InlineKeyboardButton("◀️ Назад", callback_data="admin_back")])

        reply_markup = InlineKeyboardMarkup(keyboard)
        await query.edit_message_text(
            "📝 Открытые обращения:",
            reply_markup=reply_markup
        )


async def admin_ticket_view_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """View ticket for admin"""
    query = update.callback_query
    await safe_answer_query(query)

    # Extract ticket_id from callback_data: admin_ticket_123
    parts = query.data.split("_")
    ticket_id = int(parts[-1])

    async with async_session_maker() as session:
        ticket = await TicketCRUD.get_by_id(session, ticket_id)
        if not ticket:
            await query.answer("❌ Обращение не найдено.", show_alert=True)
            return

        user_name = get_user_display_name(ticket.user)
        created = format_datetime(ticket.created_at, "%d.%m.%Y %H:%M")

        text = f"📝 *Обращение #{ticket.id}*\n\n"
        text += f"От: {user_name}\n"
        text += f"Дата: {created}\n\n"
        text += f"*{ticket.title}*\n\n"
        text += f"{ticket.description}\n"

        keyboard = [
            [InlineKeyboardButton("💬 Ответить", callback_data=f"admin_respond_{ticket.id}")],
            [InlineKeyboardButton("✅ Закрыть", callback_data=f"admin_close_{ticket.id}")],
            [InlineKeyboardButton("◀️ Назад", callback_data="admin_tickets")]
        ]

        reply_markup = InlineKeyboardMarkup(keyboard)

        # Send attachments if available
        if ticket.attachments:
            try:
                attachments = json.loads(ticket.attachments)
                for file_id in attachments:
                    await context.bot.send_document(chat_id=query.message.chat_id, document=file_id)
            except Exception:
                pass

        await query.edit_message_text(text, reply_markup=reply_markup, parse_mode='Markdown')


async def admin_respond_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Respond to ticket"""
    query = update.callback_query
    await safe_answer_query(query)

    # Extract ticket_id from callback_data: admin_respond_123
    parts = query.data.split("_")
    ticket_id = int(parts[-1])

    await query.edit_message_text(
        f"💬 Ответ на обращение #{ticket_id}\n\n"
        "Эта функция в разработке.\n\n"
        "Используйте /admin для возврата в админ-панель.",
        reply_markup=InlineKeyboardMarkup([[
            InlineKeyboardButton("◀️ Назад", callback_data=f"admin_ticket_{ticket_id}")
        ]])
    )


async def admin_close_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Close ticket"""
    query = update.callback_query
    await safe_answer_query(query)

    # Extract ticket_id from callback_data: admin_close_123
    parts = query.data.split("_")
    ticket_id = int(parts[-1])

    async with async_session_maker() as session:
        ticket = await TicketCRUD.get_by_id(session, ticket_id)
        if not ticket:
            await query.answer("❌ Обращение не найдено.", show_alert=True)
            return

        await TicketCRUD.update(
            session,
            ticket,
            status=TicketStatus.CLOSED
        )

        # Notify user
        try:
            await context.bot.send_message(
                chat_id=ticket.user.telegram_id,
                text=f"✅ Ваше обращение #{ticket.id} закрыто администратором."
            )
        except Exception:
            pass

        await query.answer("✅ Обращение закрыто.", show_alert=True)
        await admin_tickets_callback(update, context)


async def admin_emergency_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Start emergency broadcast"""
    query = update.callback_query
    await safe_answer_query(query)

    await query.edit_message_text(
        "📢 *Оповещение*\n\n"
        "Введите текст сообщения, которое будет отправлено всем членам ассоциации:",
        parse_mode='Markdown'
    )
    return EMERGENCY_MESSAGE


async def admin_emergency_send(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Send emergency message"""
    message = update.message.text.strip()

    async with async_session_maker() as session:
        verified_users = await UserCRUD.get_all_verified(session)

        sent_count = 0
        for user in verified_users:
            if user.notifications_enabled:
                try:
                    await context.bot.send_message(
                        chat_id=user.telegram_id,
                        text=f"📢 *ОПОВЕЩЕНИЕ*\n\n{message}",
                        parse_mode='Markdown'
                    )
                    sent_count += 1
                except Exception:
                    pass

    await update.message.reply_text(
        f"✅ Оповещение отправлено {sent_count} пользователям."
    )

    return ConversationHandler.END


async def admin_stats_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Show detailed statistics"""
    query = update.callback_query
    await safe_answer_query(query)

    async with async_session_maker() as session:
        from sqlalchemy import select, func
        from database.models import User, Voting, Event, Ticket

        total_users = await session.scalar(select(func.count(User.id)))
        verified_count = await session.scalar(
            select(func.count(User.id)).where(User.status == UserStatus.VERIFIED)
        )
        total_votings = await session.scalar(select(func.count(Voting.id)))
        total_events = await session.scalar(select(func.count(Event.id)))
        total_tickets = await session.scalar(select(func.count(Ticket.id)))

        text = "📊 *Статистика системы*\n\n"
        text += f"👥 Всего пользователей: {total_users}\n"
        text += f"✅ Верифицировано: {verified_count}\n\n"
        text += f"🗳️ Всего голосований: {total_votings}\n"
        text += f"📅 Всего событий: {total_events}\n"
        text += f"📝 Всего обращений: {total_tickets}\n"

        keyboard = [[InlineKeyboardButton("◀️ Назад", callback_data="admin_back")]]
        reply_markup = InlineKeyboardMarkup(keyboard)

        await query.edit_message_text(text, reply_markup=reply_markup, parse_mode='Markdown')


async def admin_votings_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Show votings management"""
    query = update.callback_query
    await safe_answer_query(query)

    async with async_session_maker() as session:
        draft_votings = await VotingCRUD.get_draft_votings(session)
        active_votings = await VotingCRUD.get_active(session)

        text = "🗳️ *Управление голосованиями*\n\n"
        text += f"📝 На модерации: {len(draft_votings)}\n"
        text += f"✅ Активных: {len(active_votings)}\n"

        keyboard = [
            [InlineKeyboardButton(f"📝 На модерации ({len(draft_votings)})", callback_data="admin_votings_draft")],
            [InlineKeyboardButton(f"✅ Активные ({len(active_votings)})", callback_data="admin_votings_active")],
            [InlineKeyboardButton("◀️ Назад", callback_data="admin_back")]
        ]

        reply_markup = InlineKeyboardMarkup(keyboard)
        await query.edit_message_text(
            text,
            reply_markup=reply_markup,
            parse_mode='Markdown'
        )


async def admin_votings_draft_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Show draft votings for moderation"""
    query = update.callback_query
    await safe_answer_query(query)

    async with async_session_maker() as session:
        draft_votings = await VotingCRUD.get_draft_votings(session)

        if not draft_votings:
            await query.edit_message_text(
                "📝 *Вопросы на модерации*\n\n"
                "Нет вопросов на модерации.",
                parse_mode='Markdown',
                reply_markup=InlineKeyboardMarkup([[
                    InlineKeyboardButton("◀️ Назад", callback_data="admin_votings")
                ]])
            )
            return

        keyboard = []
        for voting in draft_votings:
            keyboard.append([
                InlineKeyboardButton(
                    f"📝 {voting.title[:40]}...",
                    callback_data=f"admin_voting_draft_{voting.id}"
                )
            ])
        keyboard.append([InlineKeyboardButton("◀️ Назад", callback_data="admin_votings")])

        reply_markup = InlineKeyboardMarkup(keyboard)
        await query.edit_message_text(
            "📝 *Вопросы на модерации*\n\nВыберите вопрос для модерации:",
            reply_markup=reply_markup,
            parse_mode='Markdown'
        )


async def admin_votings_active_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Show active votings for management"""
    query = update.callback_query
    await safe_answer_query(query)

    async with async_session_maker() as session:
        active_votings = await VotingCRUD.get_active(session)

        if not active_votings:
            await query.edit_message_text(
                "✅ *Активные голосования*\n\n"
                "Нет активных голосований.",
                parse_mode='Markdown',
                reply_markup=InlineKeyboardMarkup([[
                    InlineKeyboardButton("◀️ Назад", callback_data="admin_votings")
                ]])
            )
            return

        keyboard = []
        for voting in active_votings:
            keyboard.append([
                InlineKeyboardButton(
                    f"✅ {voting.title[:40]}...",
                    callback_data=f"admin_voting_active_{voting.id}"
                )
            ])
        keyboard.append([InlineKeyboardButton("◀️ Назад", callback_data="admin_votings")])

        reply_markup = InlineKeyboardMarkup(keyboard)
        await query.edit_message_text(
            "✅ *Активные голосования*\n\nВыберите голосование для управления:",
            reply_markup=reply_markup,
            parse_mode='Markdown'
        )


async def admin_voting_draft_view_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """View draft voting for moderation"""
    query = update.callback_query
    await safe_answer_query(query)

    voting_id = int(query.data.split("_")[-1])

    async with async_session_maker() as session:
        voting = await VotingCRUD.get_by_id(session, voting_id)
        if not voting:
            await query.answer("❌ Голосование не найдено.", show_alert=True)
            return

        options = json.loads(voting.options) if isinstance(voting.options, str) else voting.options
        creator_name = get_user_display_name(voting.creator)
        created = format_datetime(voting.created_at, "%d.%m.%Y %H:%M")

        text = f"📝 *Вопрос на модерации*\n\n"
        text += f"*{voting.title}*\n\n"
        text += f"{voting.description}\n\n"
        text += f"*Варианты ответов:*\n"
        for i, option in enumerate(options):
            text += f"{i+1}. {option}\n"
        text += f"\nАвтор: {creator_name}\n"
        text += f"Создано: {created}\n"

        keyboard = [
            [
                InlineKeyboardButton("✅ Опубликовать", callback_data=f"admin_voting_publish_{voting_id}"),
                InlineKeyboardButton("❌ Отклонить", callback_data=f"admin_voting_reject_{voting_id}")
            ],
            [InlineKeyboardButton("◀️ Назад", callback_data="admin_votings_draft")]
        ]

        reply_markup = InlineKeyboardMarkup(keyboard)
        await query.edit_message_text(text, reply_markup=reply_markup, parse_mode='Markdown')


async def admin_voting_active_view_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """View active voting for management"""
    query = update.callback_query
    await safe_answer_query(query)

    voting_id = int(query.data.split("_")[-1])

    async with async_session_maker() as session:
        voting = await VotingCRUD.get_by_id(session, voting_id)
        if not voting:
            await query.answer("❌ Голосование не найдено.", show_alert=True)
            return

        options = json.loads(voting.options) if isinstance(voting.options, str) else voting.options
        creator_name = get_user_display_name(voting.creator)
        ends_at = format_datetime(voting.ends_at)

        text = f"✅ *Активное голосование*\n\n"
        text += f"*{voting.title}*\n\n"
        text += f"{voting.description}\n\n"
        text += f"*Варианты ответов:*\n"
        for i, option in enumerate(options):
            text += f"{i+1}. {option}\n"
        text += f"\nАвтор: {creator_name}\n"
        text += f"Завершается: {ends_at}\n"
        text += f"Голосов: {voting.total_votes}\n"

        keyboard = [
            [InlineKeyboardButton("🗑️ Удалить голосование", callback_data=f"admin_voting_delete_{voting_id}")],
            [InlineKeyboardButton("◀️ Назад", callback_data="admin_votings_active")]
        ]

        reply_markup = InlineKeyboardMarkup(keyboard)
        await query.edit_message_text(text, reply_markup=reply_markup, parse_mode='Markdown')


async def admin_voting_publish_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Publish (approve) draft voting"""
    query = update.callback_query
    await safe_answer_query(query)

    voting_id = int(query.data.split("_")[-1])

    async with async_session_maker() as session:
        voting = await VotingCRUD.get_by_id(session, voting_id)
        if not voting:
            await query.answer("❌ Голосование не найдено.", show_alert=True)
            return

        # Update status to ACTIVE and set proper dates
        starts_at = datetime.utcnow()
        ends_at = starts_at + timedelta(days=config.VOTE_DURATION_DAYS)

        await VotingCRUD.update(
            session,
            voting,
            status=VotingStatus.ACTIVE,
            starts_at=starts_at,
            ends_at=ends_at
        )

        # Notify creator
        try:
            await context.bot.send_message(
                chat_id=voting.creator.telegram_id,
                text=f"✅ Ваш вопрос одобрен и опубликован!\n\n"
                     f"*{voting.title}*\n\n"
                     f"Голосование будет активно до {format_datetime(ends_at)}.",
                parse_mode='Markdown'
            )
        except Exception:
            pass

        # Notify all verified members with voting buttons
        verified_users = await UserCRUD.get_all_verified(session)
        options = json.loads(voting.options) if isinstance(voting.options, str) else voting.options

        for user in verified_users:
            if user.notifications_enabled:
                try:
                    # Create voting message with buttons
                    text = f"🗳️ *Новое голосование!*\n\n"
                    text += f"*{voting.title}*\n\n"
                    text += f"{voting.description}\n\n"
                    text += f"Завершается: {format_datetime(ends_at)}\n\n"
                    text += "*Варианты ответов:*\n"
                    for i, option in enumerate(options):
                        text += f"{i+1}. {option}\n"

                    # Create vote buttons
                    keyboard = []
                    for i, option in enumerate(options):
                        keyboard.append([
                            InlineKeyboardButton(
                                f"✓ {option}",
                                callback_data=f"vote_cast_{voting.id}_{i}"
                            )
                        ])

                    reply_markup = InlineKeyboardMarkup(keyboard)

                    await context.bot.send_message(
                        chat_id=user.telegram_id,
                        text=text,
                        reply_markup=reply_markup,
                        parse_mode='Markdown'
                    )
                except Exception:
                    pass

    await query.answer("✅ Голосование опубликовано!", show_alert=True)
    await admin_votings_draft_callback(update, context)


async def admin_voting_reject_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Reject draft voting"""
    query = update.callback_query
    await safe_answer_query(query)

    voting_id = int(query.data.split("_")[-1])

    async with async_session_maker() as session:
        voting = await VotingCRUD.get_by_id(session, voting_id)
        if not voting:
            await query.answer("❌ Голосование не найдено.", show_alert=True)
            return

        # Update status to CANCELLED
        await VotingCRUD.update(session, voting, status=VotingStatus.CANCELLED)

        # Notify creator
        try:
            await context.bot.send_message(
                chat_id=voting.creator.telegram_id,
                text=f"❌ Ваш вопрос отклонен модератором.\n\n"
                     f"*{voting.title}*\n\n"
                     f"Вы можете предложить другой вопрос через меню голосований.",
                parse_mode='Markdown'
            )
        except Exception:
            pass

    await query.answer("✅ Вопрос отклонен.", show_alert=True)
    await admin_votings_draft_callback(update, context)


async def admin_voting_delete_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Delete (cancel) active voting"""
    query = update.callback_query
    await safe_answer_query(query)

    voting_id = int(query.data.split("_")[-1])

    async with async_session_maker() as session:
        voting = await VotingCRUD.get_by_id(session, voting_id)
        if not voting:
            await query.answer("❌ Голосование не найдено.", show_alert=True)
            return

        # Update status to CANCELLED
        await VotingCRUD.delete(session, voting)

        # Notify all members
        verified_users = await UserCRUD.get_all_verified(session)
        for user in verified_users:
            if user.notifications_enabled:
                try:
                    await context.bot.send_message(
                        chat_id=user.telegram_id,
                        text=f"⚠️ Голосование удалено администратором\n\n"
                             f"*{voting.title}*",
                        parse_mode='Markdown'
                    )
                except Exception:
                    pass

    await query.answer("✅ Голосование удалено.", show_alert=True)
    await admin_votings_active_callback(update, context)


async def admin_events_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Show events management"""
    query = update.callback_query
    await safe_answer_query(query)

    await query.edit_message_text(
        "📅 *Управление событиями*\n\n"
        "Эта функция в разработке.",
        reply_markup=InlineKeyboardMarkup([[
            InlineKeyboardButton("◀️ Назад", callback_data="admin_back")
        ]]),
        parse_mode='Markdown'
    )


async def admin_back_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle back button - return to admin panel"""
    query = update.callback_query
    await safe_answer_query(query)

    # Get fresh data and show admin panel
    async with async_session_maker() as session:
        user = await UserCRUD.get_by_telegram_id(session, update.effective_user.id)

        if not user or not user.is_admin:
            await query.edit_message_text("❌ Доступ запрещен.")
            return

        # Get statistics
        pending_users = await UserCRUD.get_pending_verification(session)
        verified_users = await UserCRUD.get_all_verified(session)
        active_votings = await VotingCRUD.get_active(session)
        upcoming_events = await EventCRUD.get_upcoming(session, limit=5)
        open_tickets = await TicketCRUD.get_open_tickets(session)

        text = "👨‍💼 *Админ-панель*\n\n"
        text += f"👥 Пользователей:\n"
        text += f"  • Членов ассоциации: {len(verified_users)}\n"
        text += f"  • На проверке: {len(pending_users)}\n\n"
        text += f"🗳️ Активных голосований: {len(active_votings)}\n"
        text += f"📅 Предстоящих событий: {len(upcoming_events)}\n"
        text += f"📝 Открытых обращений: {len(open_tickets)}\n"

        keyboard = [
            [
                InlineKeyboardButton(f"👥 Пользователи ({len(pending_users)})", callback_data="admin_users"),
                InlineKeyboardButton("🗳️ Голосования", callback_data="admin_votings")
            ],
            [
                InlineKeyboardButton("📅 События", callback_data="admin_events"),
                InlineKeyboardButton(f"📝 Обращение в ИГ ({len(open_tickets)})", callback_data="admin_tickets")
            ],
            [
                InlineKeyboardButton("📊 Статистика", callback_data="admin_stats"),
                InlineKeyboardButton("📢 Оповещение", callback_data="admin_emergency")
            ]
        ]

        reply_markup = InlineKeyboardMarkup(keyboard)
        await query.edit_message_text(
            text,
            reply_markup=reply_markup,
            parse_mode='Markdown'
        )


def register_admin_handlers(application):
    """Register admin handlers"""
    # Admin panel command
    application.add_handler(CommandHandler("admin", admin_panel))
    application.add_handler(MessageHandler(
        filters.Regex("^👨‍💼 Админ-панель$"),
        admin_panel
    ))

    # Callbacks
    application.add_handler(CallbackQueryHandler(admin_users_callback, pattern="^admin_users$"))
    application.add_handler(CallbackQueryHandler(admin_users_pending_callback, pattern="^admin_users_pending$"))
    application.add_handler(CallbackQueryHandler(admin_users_verified_callback, pattern="^admin_users_verified$"))
    application.add_handler(CallbackQueryHandler(admin_user_view_callback, pattern="^admin_user_"))
    application.add_handler(CallbackQueryHandler(admin_approve_callback, pattern="^admin_approve_"))
    application.add_handler(CallbackQueryHandler(admin_revoke_callback, pattern="^admin_revoke_"))
    application.add_handler(CallbackQueryHandler(admin_votings_callback, pattern="^admin_votings$"))
    application.add_handler(CallbackQueryHandler(admin_votings_draft_callback, pattern="^admin_votings_draft$"))
    application.add_handler(CallbackQueryHandler(admin_votings_active_callback, pattern="^admin_votings_active$"))
    application.add_handler(CallbackQueryHandler(admin_voting_draft_view_callback, pattern="^admin_voting_draft_"))
    application.add_handler(CallbackQueryHandler(admin_voting_active_view_callback, pattern="^admin_voting_active_"))
    application.add_handler(CallbackQueryHandler(admin_voting_publish_callback, pattern="^admin_voting_publish_"))
    application.add_handler(CallbackQueryHandler(admin_voting_reject_callback, pattern="^admin_voting_reject_"))
    application.add_handler(CallbackQueryHandler(admin_voting_delete_callback, pattern="^admin_voting_delete_"))
    application.add_handler(CallbackQueryHandler(admin_events_callback, pattern="^admin_events$"))
    application.add_handler(CallbackQueryHandler(admin_tickets_callback, pattern="^admin_tickets$"))
    application.add_handler(CallbackQueryHandler(admin_ticket_view_callback, pattern="^admin_ticket_"))
    application.add_handler(CallbackQueryHandler(admin_respond_callback, pattern="^admin_respond_"))
    application.add_handler(CallbackQueryHandler(admin_close_callback, pattern="^admin_close_"))
    application.add_handler(CallbackQueryHandler(admin_stats_callback, pattern="^admin_stats$"))
    application.add_handler(CallbackQueryHandler(admin_back_callback, pattern="^admin_back$"))

    # Reject user conversation
    reject_conv = ConversationHandler(
        entry_points=[CallbackQueryHandler(admin_reject_callback, pattern="^admin_reject_")],
        states={
            REJECT_REASON: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, admin_reject_reason)
            ],
        },
        fallbacks=[CommandHandler("cancel", lambda u, c: ConversationHandler.END)],
        allow_reentry=True,
        per_chat=True
    )
    application.add_handler(reject_conv)

    # Emergency broadcast conversation
    emergency_conv = ConversationHandler(
        entry_points=[CallbackQueryHandler(admin_emergency_start, pattern="^admin_emergency$")],
        states={
            EMERGENCY_MESSAGE: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, admin_emergency_send)
            ],
        },
        fallbacks=[],
        allow_reentry=True,
        per_chat=True
    )
    application.add_handler(emergency_conv)
