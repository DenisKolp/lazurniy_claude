"""
Voting system handlers
"""
from datetime import datetime, timedelta
from telegram import Update, InlineKeyboardMarkup, InlineKeyboardButton, ReplyKeyboardMarkup, KeyboardButton
from telegram.ext import (
    ContextTypes, CommandHandler, MessageHandler,
    filters, ConversationHandler, CallbackQueryHandler
)
from database.crud import UserCRUD, VotingCRUD, VoteCRUD
from database.models import UserStatus, VotingStatus
from database.session import async_session_maker
from utils.validators import validate_title, validate_description, validate_voting_options
from utils.helpers import format_datetime, calculate_quorum, format_voting_results, get_user_display_name
from config import config
import json


# Conversation states
VOTING_TITLE, VOTING_DESCRIPTION, VOTING_OPTIONS, VOTING_DURATION = range(4)
PROPOSE_TITLE, PROPOSE_DESCRIPTION, PROPOSE_OPTIONS = range(4, 7)


async def voting_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Show voting menu"""
    async with async_session_maker() as session:
        user = await UserCRUD.get_by_telegram_id(session, update.effective_user.id)

        if not user or user.status != UserStatus.VERIFIED:
            await update.message.reply_text(
                "❌ Доступ запрещен. Пройдите верификацию (/verify)."
            )
            return

        active_votings = await VotingCRUD.get_active(session)

        text = "🗳️ *Голосования*\n\n"
        if active_votings:
            text += "Активные голосования:\n\n"
            for voting in active_votings:
                ends_at = format_datetime(voting.ends_at)
                text += f"• {voting.title}\n"
                text += f"  Завершается: {ends_at}\n\n"
        else:
            text += "Нет активных голосований.\n\n"

        keyboard = [
            [InlineKeyboardButton("📊 Просмотреть активные", callback_data="voting_list")],
            [InlineKeyboardButton("➕ Предложить вопрос", callback_data="voting_propose")],
            [InlineKeyboardButton("📈 Мои вопросы", callback_data="voting_my")],
            [InlineKeyboardButton("📜 История голосований", callback_data="voting_history")]
        ]

        if user.is_admin:
            keyboard.append([InlineKeyboardButton("👨‍💼 Создать голосование", callback_data="voting_create")])

        reply_markup = InlineKeyboardMarkup(keyboard)
        await update.message.reply_text(text, reply_markup=reply_markup, parse_mode='Markdown')


async def voting_list_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Show list of active votings"""
    query = update.callback_query
    await query.answer()

    async with async_session_maker() as session:
        active_votings = await VotingCRUD.get_active(session)

        if not active_votings:
            await query.edit_message_text("Нет активных голосований.")
            return

        keyboard = []
        for voting in active_votings:
            keyboard.append([
                InlineKeyboardButton(
                    f"📊 {voting.title[:40]}...",
                    callback_data=f"voting_view_{voting.id}"
                )
            ])
        keyboard.append([InlineKeyboardButton("◀️ Назад", callback_data="voting_menu")])

        reply_markup = InlineKeyboardMarkup(keyboard)
        await query.edit_message_text(
            "Выберите голосование:",
            reply_markup=reply_markup
        )


async def voting_view_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """View voting details and vote"""
    query = update.callback_query
    await query.answer()

    voting_id = int(query.data.split("_")[2])

    async with async_session_maker() as session:
        voting = await VotingCRUD.get_by_id(session, voting_id)
        if not voting:
            await query.edit_message_text("❌ Голосование не найдено.")
            return

        user = await UserCRUD.get_by_telegram_id(session, query.from_user.id)

        # Check if user already voted
        existing_vote = await VoteCRUD.get_user_vote(session, user.id, voting_id)

        # Get current results
        results = await VoteCRUD.get_voting_results(session, voting_id)
        total_votes = await VoteCRUD.count_votes(session, voting_id)

        options = json.loads(voting.options) if isinstance(voting.options, str) else voting.options

        text = f"📊 *{voting.title}*\n\n"
        text += f"{voting.description}\n\n"
        text += f"Завершается: {format_datetime(voting.ends_at)}\n"
        text += f"Всего голосов: {total_votes}\n\n"

        if existing_vote is not None:
            text += f"✅ Вы проголосовали за вариант: {options[existing_vote.option_index]}\n\n"

        text += "*Варианты ответов:*\n"
        for i, option in enumerate(options):
            votes = results.get(i, 0)
            percent = (votes / total_votes * 100) if total_votes > 0 else 0
            text += f"{i+1}. {option} - {votes} ({percent:.1f}%)\n"

        keyboard = []
        if existing_vote is None and voting.status == VotingStatus.ACTIVE:
            for i, option in enumerate(options):
                keyboard.append([
                    InlineKeyboardButton(
                        f"✓ {option}",
                        callback_data=f"vote_cast_{voting_id}_{i}"
                    )
                ])

        keyboard.append([InlineKeyboardButton("◀️ Назад к списку", callback_data="voting_list")])

        reply_markup = InlineKeyboardMarkup(keyboard)
        await query.edit_message_text(text, reply_markup=reply_markup, parse_mode='Markdown')


async def vote_cast_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Cast a vote"""
    query = update.callback_query
    await query.answer()

    parts = query.data.split("_")
    voting_id = int(parts[2])
    option_index = int(parts[3])

    async with async_session_maker() as session:
        user = await UserCRUD.get_by_telegram_id(session, query.from_user.id)
        voting = await VotingCRUD.get_by_id(session, voting_id)

        if not voting or voting.status != VotingStatus.ACTIVE:
            await query.answer("❌ Голосование не активно.", show_alert=True)
            return

        # Check if already voted
        existing_vote = await VoteCRUD.get_user_vote(session, user.id, voting_id)
        if existing_vote:
            await query.answer("❌ Вы уже проголосовали!", show_alert=True)
            return

        # Create vote
        await VoteCRUD.create(
            session,
            user_id=user.id,
            voting_id=voting_id,
            option_index=option_index
        )

        # Update voting
        total_votes = await VoteCRUD.count_votes(session, voting_id)
        await VotingCRUD.update(session, voting, total_votes=total_votes)

        options = json.loads(voting.options) if isinstance(voting.options, str) else voting.options
        await query.answer(f"✅ Ваш голос учтен: {options[option_index]}", show_alert=True)

        # Refresh view
        await voting_view_callback(update, context)


async def voting_create_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Start creating a new voting"""
    query = update.callback_query
    await query.answer()

    async with async_session_maker() as session:
        user = await UserCRUD.get_by_telegram_id(session, query.from_user.id)
        if not user or not user.is_admin:
            await query.answer("❌ Доступ запрещен.", show_alert=True)
            return

    await query.edit_message_text(
        "📝 *Создание голосования*\n\n"
        "Шаг 1/4: Введите название голосования:",
        parse_mode='Markdown'
    )
    return VOTING_TITLE


async def voting_receive_title(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Receive voting title"""
    title = update.message.text.strip()

    if not validate_title(title):
        await update.message.reply_text(
            "❌ Название должно быть от 5 до 500 символов. Попробуйте еще раз:"
        )
        return VOTING_TITLE

    context.user_data['voting_title'] = title
    await update.message.reply_text(
        "✅ Название сохранено!\n\n"
        "Шаг 2/4: Введите описание голосования:"
    )
    return VOTING_DESCRIPTION


async def voting_receive_description(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Receive voting description"""
    description = update.message.text.strip()

    if not validate_description(description):
        await update.message.reply_text(
            "❌ Описание должно быть от 10 до 4000 символов. Попробуйте еще раз:"
        )
        return VOTING_DESCRIPTION

    context.user_data['voting_description'] = description
    await update.message.reply_text(
        "✅ Описание сохранено!\n\n"
        "Шаг 3/4: Введите варианты ответов (каждый с новой строки, минимум 2):\n\n"
        "Пример:\n"
        "За\n"
        "Против\n"
        "Воздержался"
    )
    return VOTING_OPTIONS


async def voting_receive_options(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Receive voting options"""
    options = [opt.strip() for opt in update.message.text.split('\n') if opt.strip()]

    if not validate_voting_options(options):
        await update.message.reply_text(
            "❌ Необходимо от 2 до 10 вариантов. Попробуйте еще раз:"
        )
        return VOTING_OPTIONS

    context.user_data['voting_options'] = options
    await update.message.reply_text(
        "✅ Варианты сохранены!\n\n"
        f"Шаг 4/4: Введите длительность голосования в днях (по умолчанию {config.VOTE_DURATION_DAYS}):"
    )
    return VOTING_DURATION


async def voting_receive_duration(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Receive voting duration and create voting"""
    duration_text = update.message.text.strip()

    try:
        duration_days = int(duration_text)
        if duration_days < 1 or duration_days > 30:
            raise ValueError()
    except ValueError:
        await update.message.reply_text(
            "❌ Длительность должна быть от 1 до 30 дней. Попробуйте еще раз:"
        )
        return VOTING_DURATION

    async with async_session_maker() as session:
        user = await UserCRUD.get_by_telegram_id(session, update.effective_user.id)

        starts_at = datetime.utcnow()
        ends_at = starts_at + timedelta(days=duration_days)

        voting = await VotingCRUD.create(
            session,
            title=context.user_data['voting_title'],
            description=context.user_data['voting_description'],
            options=json.dumps(context.user_data['voting_options']),
            creator_id=user.id,
            status=VotingStatus.ACTIVE,
            starts_at=starts_at,
            ends_at=ends_at,
            quorum_percent=config.DEFAULT_QUORUM_PERCENT
        )

    await update.message.reply_text(
        f"✅ Голосование создано!\n\n"
        f"ID: {voting.id}\n"
        f"Название: {voting.title}\n"
        f"Завершится: {format_datetime(ends_at)}\n\n"
        "Голосование активно и доступно всем участникам."
    )

    # Notify all association members
    async with async_session_maker() as session:
        verified_users = await UserCRUD.get_all_verified(session)
        for verified_user in verified_users:
            if verified_user.notifications_enabled and verified_user.telegram_id != user.telegram_id:
                try:
                    await context.bot.send_message(
                        chat_id=verified_user.telegram_id,
                        text=f"🗳️ Новое голосование!\n\n"
                             f"*{voting.title}*\n\n"
                             f"{voting.description[:200]}...\n\n"
                             f"Используйте команду /voting для участия.",
                        parse_mode='Markdown'
                    )
                except Exception:
                    pass

    context.user_data.clear()
    return ConversationHandler.END


async def voting_propose_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Start proposing a question"""
    query = update.callback_query
    await query.answer()

    async with async_session_maker() as session:
        user = await UserCRUD.get_by_telegram_id(session, query.from_user.id)
        if not user or user.status != UserStatus.VERIFIED:
            await query.answer("❌ Доступ запрещен.", show_alert=True)
            return

    await query.edit_message_text(
        "➕ *Предложить вопрос для голосования*\n\n"
        "Шаг 1/3: Введите название вопроса:",
        parse_mode='Markdown'
    )
    return PROPOSE_TITLE


async def propose_receive_title(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Receive proposed question title"""
    title = update.message.text.strip()

    if not validate_title(title):
        await update.message.reply_text(
            "❌ Название должно быть от 5 до 500 символов. Попробуйте еще раз:"
        )
        return PROPOSE_TITLE

    context.user_data['propose_title'] = title
    await update.message.reply_text(
        "✅ Название сохранено!\n\n"
        "Шаг 2/3: Введите описание вопроса:"
    )
    return PROPOSE_DESCRIPTION


async def propose_receive_description(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Receive proposed question description"""
    description = update.message.text.strip()

    if not validate_description(description):
        await update.message.reply_text(
            "❌ Описание должно быть от 10 до 4000 символов. Попробуйте еще раз:"
        )
        return PROPOSE_DESCRIPTION

    context.user_data['propose_description'] = description
    await update.message.reply_text(
        "✅ Описание сохранено!\n\n"
        "Шаг 3/3: Введите варианты ответов (каждый с новой строки, минимум 2):\n\n"
        "Пример:\n"
        "За\n"
        "Против\n"
        "Воздержался"
    )
    return PROPOSE_OPTIONS


async def propose_receive_options(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Receive proposed question options and create draft voting"""
    options = [opt.strip() for opt in update.message.text.split('\n') if opt.strip()]

    if not validate_voting_options(options):
        await update.message.reply_text(
            "❌ Необходимо от 2 до 10 вариантов. Попробуйте еще раз:"
        )
        return PROPOSE_OPTIONS

    async with async_session_maker() as session:
        user = await UserCRUD.get_by_telegram_id(session, update.effective_user.id)

        # Create draft voting (not active yet)
        voting = await VotingCRUD.create(
            session,
            title=context.user_data['propose_title'],
            description=context.user_data['propose_description'],
            options=json.dumps(options),
            creator_id=user.id,
            status=VotingStatus.DRAFT,
            starts_at=datetime.utcnow(),
            ends_at=datetime.utcnow() + timedelta(days=config.VOTE_DURATION_DAYS),
            quorum_percent=config.DEFAULT_QUORUM_PERCENT
        )

    await update.message.reply_text(
        f"✅ Вопрос предложен!\n\n"
        f"Название: {voting.title}\n\n"
        "Ваш вопрос отправлен на модерацию администраторам.\n"
        "После одобрения он будет опубликован для всех участников."
    )

    # Notify admins about new proposed question
    async with async_session_maker() as session:
        all_users = await UserCRUD.get_all_verified(session)
        admin_users = [u for u in all_users if u.is_admin]

        for admin in admin_users:
            try:
                await context.bot.send_message(
                    chat_id=admin.telegram_id,
                    text=f"📝 Новый вопрос на модерацию!\n\n"
                         f"*{voting.title}*\n\n"
                         f"От: {get_user_display_name(user)}\n\n"
                         f"Перейдите в админ-панель для модерации.",
                    parse_mode='Markdown'
                )
            except Exception:
                pass

    context.user_data.clear()
    return ConversationHandler.END


async def voting_my_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Show user's proposed questions"""
    query = update.callback_query
    await query.answer()

    async with async_session_maker() as session:
        user = await UserCRUD.get_by_telegram_id(session, query.from_user.id)
        my_votings = await VotingCRUD.get_user_votings(session, user.id)

        if not my_votings:
            await query.edit_message_text(
                "📈 *Мои вопросы*\n\n"
                "У вас пока нет созданных голосований.",
                parse_mode='Markdown',
                reply_markup=InlineKeyboardMarkup([[
                    InlineKeyboardButton("◀️ Назад", callback_data="voting_back")
                ]])
            )
            return

        text = "📈 *Мои вопросы*\n\n"
        keyboard = []

        for voting in my_votings:
            status_emoji = {
                VotingStatus.ACTIVE: "✅",
                VotingStatus.COMPLETED: "📊",
                VotingStatus.CANCELLED: "❌"
            }.get(voting.status, "❓")

            text += f"{status_emoji} {voting.title}\n"
            text += f"Создано: {format_datetime(voting.created_at, '%d.%m.%Y')}\n"
            text += f"Статус: {voting.status.value}\n\n"

            keyboard.append([
                InlineKeyboardButton(
                    f"{status_emoji} {voting.title[:30]}",
                    callback_data=f"voting_view_{voting.id}"
                )
            ])

        keyboard.append([InlineKeyboardButton("◀️ Назад", callback_data="voting_back")])
        reply_markup = InlineKeyboardMarkup(keyboard)

        await query.edit_message_text(
            text,
            reply_markup=reply_markup,
            parse_mode='Markdown'
        )


async def voting_history_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Show completed votings history"""
    query = update.callback_query
    await query.answer()

    async with async_session_maker() as session:
        completed_votings = await VotingCRUD.get_completed(session)

        if not completed_votings:
            await query.edit_message_text(
                "📜 *История голосований*\n\n"
                "Нет завершенных голосований.",
                parse_mode='Markdown',
                reply_markup=InlineKeyboardMarkup([[
                    InlineKeyboardButton("◀️ Назад", callback_data="voting_back")
                ]])
            )
            return

        text = "📜 *История голосований*\n\n"
        keyboard = []

        for voting in completed_votings:
            ended = format_datetime(voting.ends_at, '%d.%m.%Y')
            text += f"✅ {voting.title}\n"
            text += f"Завершено: {ended}\n"
            text += f"Голосов: {voting.total_votes}\n\n"

            keyboard.append([
                InlineKeyboardButton(
                    f"📊 {voting.title[:35]}...",
                    callback_data=f"voting_view_{voting.id}"
                )
            ])

        keyboard.append([InlineKeyboardButton("◀️ Назад", callback_data="voting_back")])
        reply_markup = InlineKeyboardMarkup(keyboard)

        await query.edit_message_text(
            text,
            reply_markup=reply_markup,
            parse_mode='Markdown'
        )


async def voting_back_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Return to voting menu"""
    query = update.callback_query
    await query.answer()

    await query.delete_message()

    # Recreate update to call voting_menu
    update.message = update.effective_message
    await voting_menu(update, context)


def register_voting_handlers(application):
    """Register voting handlers"""
    # Voting menu
    application.add_handler(MessageHandler(
        filters.Regex("^🗳️ Голосования$"),
        voting_menu
    ))

    # Callbacks
    application.add_handler(CallbackQueryHandler(voting_list_callback, pattern="^voting_list$"))
    application.add_handler(CallbackQueryHandler(voting_view_callback, pattern="^voting_view_"))
    application.add_handler(CallbackQueryHandler(vote_cast_callback, pattern="^vote_cast_"))
    application.add_handler(CallbackQueryHandler(voting_create_start, pattern="^voting_create$"))
    application.add_handler(CallbackQueryHandler(voting_my_callback, pattern="^voting_my$"))
    application.add_handler(CallbackQueryHandler(voting_history_callback, pattern="^voting_history$"))
    application.add_handler(CallbackQueryHandler(voting_back_callback, pattern="^voting_back$"))

    # Create voting conversation
    create_voting_conv = ConversationHandler(
        entry_points=[CallbackQueryHandler(voting_create_start, pattern="^voting_create$")],
        states={
            VOTING_TITLE: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, voting_receive_title)
            ],
            VOTING_DESCRIPTION: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, voting_receive_description)
            ],
            VOTING_OPTIONS: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, voting_receive_options)
            ],
            VOTING_DURATION: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, voting_receive_duration)
            ],
        },
        fallbacks=[],
        allow_reentry=True,
        per_chat=True
    )
    application.add_handler(create_voting_conv)

    # Propose voting conversation
    propose_voting_conv = ConversationHandler(
        entry_points=[CallbackQueryHandler(voting_propose_callback, pattern="^voting_propose$")],
        states={
            PROPOSE_TITLE: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, propose_receive_title)
            ],
            PROPOSE_DESCRIPTION: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, propose_receive_description)
            ],
            PROPOSE_OPTIONS: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, propose_receive_options)
            ],
        },
        fallbacks=[],
        allow_reentry=True,
        per_chat=True
    )
    application.add_handler(propose_voting_conv)
