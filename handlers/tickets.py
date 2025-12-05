"""
Initiative group (tickets) handlers
"""
from telegram import Update, InlineKeyboardMarkup, InlineKeyboardButton
from telegram.ext import (
    ContextTypes, CommandHandler, MessageHandler,
    filters, ConversationHandler, CallbackQueryHandler
)
from database.crud import UserCRUD, TicketCRUD
from database.models import UserStatus, TicketStatus
from database.session import async_session_maker
from utils.validators import validate_title, validate_description, validate_document
from utils.helpers import format_datetime
import json


# Conversation states
TICKET_TITLE, TICKET_DESCRIPTION, TICKET_ATTACHMENTS = range(3)


async def tickets_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Show tickets menu"""
    async with async_session_maker() as session:
        user = await UserCRUD.get_by_telegram_id(session, update.effective_user.id)

        if not user or user.status != UserStatus.VERIFIED:
            await update.message.reply_text(
                "❌ Доступ запрещен. Пройдите верификацию (/verify)."
            )
            return

        user_tickets = await TicketCRUD.get_user_tickets(session, user.id)

        text = "📝 *Обращение в ИГ*\n\n"
        if user_tickets:
            text += "Ваши обращения:\n\n"
            for ticket in user_tickets[:5]:
                created = format_datetime(ticket.created_at, "%d.%m.%Y")
                status_emoji = {
                    TicketStatus.NEW: "🆕",
                    TicketStatus.IN_PROGRESS: "⏳",
                    TicketStatus.ANSWERED: "✅",
                    TicketStatus.CLOSED: "✔️"
                }.get(ticket.status, "❓")

                text += f"{status_emoji} {ticket.title[:40]}\n"
                text += f"  Создано: {created}\n\n"
        else:
            text += "У вас пока нет обращений.\n\n"

        keyboard = [
            [InlineKeyboardButton("📋 Мои обращения", callback_data="tickets_my")],
            [InlineKeyboardButton("➕ Создать обращение", callback_data="ticket_create")],
        ]

        reply_markup = InlineKeyboardMarkup(keyboard)
        await update.message.reply_text(text, reply_markup=reply_markup, parse_mode='Markdown')


async def tickets_menu_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Show tickets menu (callback version)"""
    query = update.callback_query
    await query.answer()

    async with async_session_maker() as session:
        user = await UserCRUD.get_by_telegram_id(session, query.from_user.id)

        if not user or user.status != UserStatus.VERIFIED:
            await query.edit_message_text(
                "❌ Доступ запрещен. Пройдите верификацию."
            )
            return

        user_tickets = await TicketCRUD.get_user_tickets(session, user.id)

        text = "📝 *Обращение в ИГ*\n\n"
        if user_tickets:
            text += "Ваши обращения:\n\n"
            for ticket in user_tickets[:5]:
                created = format_datetime(ticket.created_at, "%d.%m.%Y")
                status_emoji = {
                    TicketStatus.NEW: "🆕",
                    TicketStatus.IN_PROGRESS: "⏳",
                    TicketStatus.ANSWERED: "✅",
                    TicketStatus.CLOSED: "✔️"
                }.get(ticket.status, "❓")

                text += f"{status_emoji} {ticket.title[:40]}\n"
                text += f"  Создано: {created}\n\n"
        else:
            text += "У вас пока нет обращений.\n\n"

        keyboard = [
            [InlineKeyboardButton("📋 Мои обращения", callback_data="tickets_my")],
            [InlineKeyboardButton("➕ Создать обращение", callback_data="ticket_create")],
        ]

        reply_markup = InlineKeyboardMarkup(keyboard)
        await query.edit_message_text(text, reply_markup=reply_markup, parse_mode='Markdown')


async def tickets_my_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Show user's tickets"""
    query = update.callback_query
    await query.answer()

    async with async_session_maker() as session:
        user = await UserCRUD.get_by_telegram_id(session, query.from_user.id)
        user_tickets = await TicketCRUD.get_user_tickets(session, user.id)

        if not user_tickets:
            await query.edit_message_text("У вас нет обращений.")
            return

        keyboard = []
        for ticket in user_tickets:
            status_emoji = {
                TicketStatus.NEW: "🆕",
                TicketStatus.IN_PROGRESS: "⏳",
                TicketStatus.ANSWERED: "✅",
                TicketStatus.CLOSED: "✔️"
            }.get(ticket.status, "❓")

            keyboard.append([
                InlineKeyboardButton(
                    f"{status_emoji} {ticket.title[:35]}",
                    callback_data=f"ticket_view_{ticket.id}"
                )
            ])
        keyboard.append([InlineKeyboardButton("◀️ Назад", callback_data="tickets_menu")])

        reply_markup = InlineKeyboardMarkup(keyboard)
        await query.edit_message_text(
            "Ваши обращения:",
            reply_markup=reply_markup
        )


async def ticket_view_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """View ticket details"""
    query = update.callback_query
    await query.answer()

    ticket_id = int(query.data.split("_")[2])

    async with async_session_maker() as session:
        ticket = await TicketCRUD.get_by_id(session, ticket_id)
        if not ticket:
            await query.edit_message_text("❌ Обращение не найдено.")
            return

        user = await UserCRUD.get_by_telegram_id(session, query.from_user.id)

        # Check access rights
        if ticket.user_id != user.id and not user.is_admin:
            await query.answer("❌ Доступ запрещен.", show_alert=True)
            return

        status_text = {
            TicketStatus.NEW: "🆕 Новое",
            TicketStatus.IN_PROGRESS: "⏳ В работе",
            TicketStatus.ANSWERED: "✅ Отвечено",
            TicketStatus.CLOSED: "✔️ Закрыто"
        }.get(ticket.status, "❓ Неизвестно")

        created = format_datetime(ticket.created_at, "%d.%m.%Y %H:%M")

        text = f"📝 *Обращение #{ticket.id}*\n\n"
        text += f"*{ticket.title}*\n\n"
        text += f"{ticket.description}\n\n"
        text += f"Статус: {status_text}\n"
        text += f"Создано: {created}\n"

        if ticket.response:
            responded = format_datetime(ticket.responded_at, "%d.%m.%Y %H:%M")
            text += f"\n*Ответ:*\n{ticket.response}\n"
            text += f"Дата ответа: {responded}\n"

        keyboard = []
        if user.is_admin and ticket.status in [TicketStatus.NEW, TicketStatus.IN_PROGRESS]:
            keyboard.append([
                InlineKeyboardButton("💬 Ответить", callback_data=f"ticket_respond_{ticket.id}")
            ])

        keyboard.append([InlineKeyboardButton("◀️ Назад", callback_data="tickets_my")])

        reply_markup = InlineKeyboardMarkup(keyboard)
        await query.edit_message_text(text, reply_markup=reply_markup, parse_mode='Markdown')


async def ticket_create_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Start creating a new ticket"""
    query = update.callback_query
    await query.answer()

    await query.edit_message_text(
        "📝 *Создание обращения*\n\n"
        "Шаг 1/3: Введите краткое название обращения:",
        parse_mode='Markdown'
    )
    return TICKET_TITLE


async def ticket_receive_title(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Receive ticket title"""
    title = update.message.text.strip()

    if not validate_title(title):
        await update.message.reply_text(
            "❌ Название должно быть от 5 до 500 символов. Попробуйте еще раз:"
        )
        return TICKET_TITLE

    context.user_data['ticket_title'] = title
    await update.message.reply_text(
        "✅ Название сохранено!\n\n"
        "Шаг 2/3: Введите подробное описание проблемы или предложения:"
    )
    return TICKET_DESCRIPTION


async def ticket_receive_description(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Receive ticket description"""
    description = update.message.text.strip()

    if not validate_description(description):
        await update.message.reply_text(
            "❌ Описание должно быть от 10 до 4000 символов. Попробуйте еще раз:"
        )
        return TICKET_DESCRIPTION

    context.user_data['ticket_description'] = description
    await update.message.reply_text(
        "✅ Описание сохранено!\n\n"
        "Шаг 3/3: Прикрепите файлы (фото, PDF) или напишите 'пропустить':"
    )
    return TICKET_ATTACHMENTS


async def ticket_receive_attachments(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Receive ticket attachments"""
    if update.message.text and update.message.text.strip().lower() == 'пропустить':
        await create_ticket(update, context)
        return ConversationHandler.END

    if update.message.document:
        file = update.message.document
        if validate_document(file.file_name):
            if 'ticket_attachments' not in context.user_data:
                context.user_data['ticket_attachments'] = []
            context.user_data['ticket_attachments'].append(file.file_id)

            await update.message.reply_text(
                f"✅ Файл '{file.file_name}' добавлен!\n"
                f"Всего файлов: {len(context.user_data['ticket_attachments'])}\n\n"
                f"Отправьте еще файлы или напишите 'готово' для завершения."
            )
            return TICKET_ATTACHMENTS
        else:
            await update.message.reply_text(
                "❌ Неподдерживаемый формат файла. Попробуйте еще раз."
            )
            return TICKET_ATTACHMENTS

    elif update.message.photo:
        photo = update.message.photo[-1]
        if 'ticket_attachments' not in context.user_data:
            context.user_data['ticket_attachments'] = []
        context.user_data['ticket_attachments'].append(photo.file_id)

        await update.message.reply_text(
            f"✅ Фото добавлено!\n"
            f"Всего файлов: {len(context.user_data['ticket_attachments'])}\n\n"
            f"Отправьте еще файлы или напишите 'готово' для завершения."
        )
        return TICKET_ATTACHMENTS

    elif update.message.text and update.message.text.strip().lower() == 'готово':
        await create_ticket(update, context)
        return ConversationHandler.END

    else:
        await update.message.reply_text(
            "Отправьте файл, фото или напишите 'готово' для завершения."
        )
        return TICKET_ATTACHMENTS


async def create_ticket(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Create ticket in database"""
    async with async_session_maker() as session:
        user = await UserCRUD.get_by_telegram_id(session, update.effective_user.id)

        attachments = context.user_data.get('ticket_attachments', [])

        ticket = await TicketCRUD.create(
            session,
            user_id=user.id,
            title=context.user_data['ticket_title'],
            description=context.user_data['ticket_description'],
            attachments=json.dumps(attachments) if attachments else None,
            status=TicketStatus.NEW
        )

    await update.message.reply_text(
        f"✅ Обращение создано!\n\n"
        f"Номер обращения: #{ticket.id}\n"
        f"Название: {ticket.title}\n\n"
        "Ваше обращение направлено в инициативную группу.\n"
        "Вы получите уведомление, когда на него ответят."
    )

    # Notify admins
    from config import config
    for admin_id in config.ADMIN_IDS:
        try:
            await context.bot.send_message(
                chat_id=admin_id,
                text=f"🔔 Новое обращение #{ticket.id}\n\n"
                     f"*{ticket.title}*\n\n"
                     f"{ticket.description[:200]}...\n\n"
                     f"Используйте /admin для просмотра.",
                parse_mode='Markdown'
            )
        except Exception:
            pass

    context.user_data.clear()


def register_tickets_handlers(application):
    """Register tickets handlers"""
    # Tickets menu
    application.add_handler(MessageHandler(
        filters.Regex("^📝 Обращение в ИГ$"),
        tickets_menu
    ))

    # Callbacks
    application.add_handler(CallbackQueryHandler(tickets_menu_callback, pattern="^tickets_menu$"))
    application.add_handler(CallbackQueryHandler(tickets_my_callback, pattern="^tickets_my$"))
    application.add_handler(CallbackQueryHandler(ticket_view_callback, pattern="^ticket_view_"))

    # Create ticket conversation
    create_ticket_conv = ConversationHandler(
        entry_points=[CallbackQueryHandler(ticket_create_start, pattern="^ticket_create$")],
        states={
            TICKET_TITLE: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, ticket_receive_title)
            ],
            TICKET_DESCRIPTION: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, ticket_receive_description)
            ],
            TICKET_ATTACHMENTS: [
                MessageHandler(
                    (filters.TEXT | filters.Document.ALL | filters.PHOTO) & ~filters.COMMAND,
                    ticket_receive_attachments
                )
            ],
        },
        fallbacks=[],
        allow_reentry=True,
        per_chat=True
    )
    application.add_handler(create_ticket_conv)
