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
from utils.validators import validate_title, validate_description
from utils.helpers import format_datetime, calculate_quorum, format_voting_results, get_user_display_name
from config import config
from services.yandex_disk_service import yandex_disk_service
import json
import asyncio
import logging

logger = logging.getLogger(__name__)


# Conversation states
VOTING_TITLE, VOTING_DESCRIPTION = range(2)
PROPOSE_DESCRIPTION = 2


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
            text += "Активные вопросы:\n\n"
            for voting in active_votings:
                ends_at = format_datetime(voting.ends_at)
                text += f"• {voting.title}\n"
                text += f"  Завершается: {ends_at}\n\n"
        else:
            text += "Нет активных вопросов.\n\n"

        keyboard = [
            [InlineKeyboardButton("📊 Просмотреть активные вопросы", callback_data="voting_list")],
            [InlineKeyboardButton("➕ Предложить вопрос", callback_data="voting_propose")]
        ]

        # Removed: Create voting button (admin uses voting propose and approves it)

        reply_markup = InlineKeyboardMarkup(keyboard)
        await update.message.reply_text(text, reply_markup=reply_markup, parse_mode='Markdown')


async def voting_menu_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Show voting menu (callback version)"""
    query = update.callback_query
    await query.answer()

    async with async_session_maker() as session:
        user = await UserCRUD.get_by_telegram_id(session, update.effective_user.id)

        if not user or user.status != UserStatus.VERIFIED:
            await query.edit_message_text(
                "❌ Доступ запрещен. Пройдите верификацию (/verify)."
            )
            return

        active_votings = await VotingCRUD.get_active(session)

        text = "🗳️ *Голосования*\n\n"
        if active_votings:
            text += "Активные вопросы:\n\n"
            for voting in active_votings:
                ends_at = format_datetime(voting.ends_at)
                text += f"• {voting.title}\n"
                text += f"  Завершается: {ends_at}\n\n"
        else:
            text += "Нет активных вопросов.\n\n"

        keyboard = [
            [InlineKeyboardButton("📊 Просмотреть активные вопросы", callback_data="voting_list")],
            [InlineKeyboardButton("➕ Предложить вопрос", callback_data="voting_propose")]
        ]

        # Removed: Create voting button (admin uses voting propose and approves it)

        reply_markup = InlineKeyboardMarkup(keyboard)
        await query.edit_message_text(text, reply_markup=reply_markup, parse_mode='Markdown')


async def voting_list_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Show all active votings as separate messages"""
    query = update.callback_query
    await query.answer()

    # Delete the menu message
    try:
        await query.message.delete()
    except Exception:
        pass

    async with async_session_maker() as session:
        active_votings = await VotingCRUD.get_active(session)

        if not active_votings:
            await context.bot.send_message(
                chat_id=query.from_user.id,
                text="Нет активных вопросов."
            )
            return

        user = await UserCRUD.get_by_telegram_id(session, query.from_user.id)

        # Send each voting as a separate message
        for voting in active_votings:
            # Check if user already voted
            existing_vote = await VoteCRUD.get_user_vote(session, user.id, voting.id)

            # Get current results
            results = await VoteCRUD.get_voting_results(session, voting.id)
            total_votes = await VoteCRUD.count_votes(session, voting.id)

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
            # Allow voting only if user hasn't voted yet and voting is active
            if existing_vote is None and voting.status == VotingStatus.ACTIVE:
                for i, option in enumerate(options):
                    keyboard.append([
                        InlineKeyboardButton(
                            f"✓ {option}",
                            callback_data=f"vote_cast_{voting.id}_{i}"
                        )
                    ])
            # Add revote button if user already voted and voting is still active
            elif existing_vote is not None and voting.status == VotingStatus.ACTIVE:
                keyboard.append([
                    InlineKeyboardButton(
                        "🔄 Переголосовать",
                        callback_data=f"vote_revote_{voting.id}"
                    )
                ])

            # Add manual end voting button for admins
            if user.is_admin and voting.status == VotingStatus.ACTIVE:
                keyboard.append([InlineKeyboardButton("⏹️ Завершить голосование", callback_data=f"voting_end_{voting.id}")])

            reply_markup = InlineKeyboardMarkup(keyboard) if keyboard else None

            await context.bot.send_message(
                chat_id=query.from_user.id,
                text=text,
                reply_markup=reply_markup,
                parse_mode='Markdown'
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
        # Add revote button if user already voted and voting is still active
        elif existing_vote is not None and voting.status == VotingStatus.ACTIVE:
            keyboard.append([
                InlineKeyboardButton(
                    "🔄 Переголосовать",
                    callback_data=f"vote_revote_{voting_id}"
                )
            ])

        # Add manual end voting button for admins
        if user.is_admin and voting.status == VotingStatus.ACTIVE:
            keyboard.append([InlineKeyboardButton("⏹️ Завершить голосование", callback_data=f"voting_end_{voting_id}")])

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

        # Check if already voted - if yes, show error
        existing_vote = await VoteCRUD.get_user_vote(session, user.id, voting_id)
        if existing_vote:
            await query.answer("❌ Вы уже проголосовали в этом голосовании.", show_alert=True)
            return

        # Create new vote
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

        # Update the message with new results
        results = await VoteCRUD.get_voting_results(session, voting_id)
        total_votes = await VoteCRUD.count_votes(session, voting_id)

        text = f"📊 *{voting.title}*\n\n"
        text += f"{voting.description}\n\n"
        text += f"Завершается: {format_datetime(voting.ends_at)}\n"
        text += f"Всего голосов: {total_votes}\n\n"
        text += f"✅ Вы проголосовали за вариант: {options[option_index]}\n\n"
        text += "*Варианты ответов:*\n"
        for i, option in enumerate(options):
            votes = results.get(i, 0)
            percent = (votes / total_votes * 100) if total_votes > 0 else 0
            text += f"{i+1}. {option} - {votes} ({percent:.1f}%)\n"

        # Show revote button and admin buttons
        keyboard = []
        # Add revote button for the user who just voted
        keyboard.append([
            InlineKeyboardButton(
                "🔄 Переголосовать",
                callback_data=f"vote_revote_{voting_id}"
            )
        ])

        # Add end button for admins
        if user.is_admin and voting.status == VotingStatus.ACTIVE:
            keyboard.append([InlineKeyboardButton("⏹️ Завершить голосование", callback_data=f"voting_end_{voting_id}")])

        reply_markup = InlineKeyboardMarkup(keyboard) if keyboard else None
        await query.edit_message_text(text, reply_markup=reply_markup, parse_mode='Markdown')


async def vote_revote_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Show voting options again for revote"""
    query = update.callback_query
    await query.answer()

    voting_id = int(query.data.split("_")[2])

    async with async_session_maker() as session:
        voting = await VotingCRUD.get_by_id(session, voting_id)
        if not voting:
            await query.answer("❌ Голосование не найдено.", show_alert=True)
            return

        if voting.status != VotingStatus.ACTIVE:
            await query.answer("❌ Голосование не активно.", show_alert=True)
            return

        user = await UserCRUD.get_by_telegram_id(session, query.from_user.id)
        existing_vote = await VoteCRUD.get_user_vote(session, user.id, voting_id)

        if existing_vote is None:
            await query.answer("❌ Вы еще не голосовали в этом голосовании.", show_alert=True)
            return

        # Get current results
        results = await VoteCRUD.get_voting_results(session, voting_id)
        total_votes = await VoteCRUD.count_votes(session, voting_id)

        options = json.loads(voting.options) if isinstance(voting.options, str) else voting.options

        text = f"📊 *{voting.title}*\n\n"
        text += f"{voting.description}\n\n"
        text += f"Завершается: {format_datetime(voting.ends_at)}\n"
        text += f"Всего голосов: {total_votes}\n\n"
        text += f"✅ Текущий выбор: {options[existing_vote.option_index]}\n\n"
        text += "*Выберите новый вариант:*\n"
        for i, option in enumerate(options):
            votes = results.get(i, 0)
            percent = (votes / total_votes * 100) if total_votes > 0 else 0
            text += f"{i+1}. {option} - {votes} ({percent:.1f}%)\n"

        # Show all voting options with revote prefix
        keyboard = []
        for i, option in enumerate(options):
            keyboard.append([
                InlineKeyboardButton(
                    f"✓ {option}",
                    callback_data=f"vote_recast_{voting_id}_{i}"
                )
            ])

        keyboard.append([InlineKeyboardButton("◀️ Отмена", callback_data=f"voting_view_{voting_id}")])

        reply_markup = InlineKeyboardMarkup(keyboard)
        await query.edit_message_text(text, reply_markup=reply_markup, parse_mode='Markdown')


async def vote_recast_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Update an existing vote (revote)"""
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

        # Get existing vote
        existing_vote = await VoteCRUD.get_user_vote(session, user.id, voting_id)
        if not existing_vote:
            await query.answer("❌ Вы еще не голосовали в этом голосовании.", show_alert=True)
            return

        old_option_index = existing_vote.option_index

        # Update the vote
        await VoteCRUD.update(
            session,
            existing_vote,
            option_index=option_index
        )

        options = json.loads(voting.options) if isinstance(voting.options, str) else voting.options
        await query.answer(f"✅ Голос изменен: {options[option_index]}", show_alert=True)

        # Update the message with new results
        results = await VoteCRUD.get_voting_results(session, voting_id)
        total_votes = await VoteCRUD.count_votes(session, voting_id)

        text = f"📊 *{voting.title}*\n\n"
        text += f"{voting.description}\n\n"
        text += f"Завершается: {format_datetime(voting.ends_at)}\n"
        text += f"Всего голосов: {total_votes}\n\n"
        text += f"✅ Вы проголосовали за вариант: {options[option_index]}\n\n"
        text += "*Варианты ответов:*\n"
        for i, option in enumerate(options):
            votes = results.get(i, 0)
            percent = (votes / total_votes * 100) if total_votes > 0 else 0
            text += f"{i+1}. {option} - {votes} ({percent:.1f}%)\n"

        # Show revote button and admin buttons
        keyboard = []
        keyboard.append([
            InlineKeyboardButton(
                "🔄 Переголосовать",
                callback_data=f"vote_revote_{voting_id}"
            )
        ])

        if user.is_admin and voting.status == VotingStatus.ACTIVE:
            keyboard.append([InlineKeyboardButton("⏹️ Завершить голосование", callback_data=f"voting_end_{voting_id}")])

        reply_markup = InlineKeyboardMarkup(keyboard) if keyboard else None
        await query.edit_message_text(text, reply_markup=reply_markup, parse_mode='Markdown')


async def voting_end_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Manually end all active votings (admin only)"""
    query = update.callback_query
    await query.answer()

    async with async_session_maker() as session:
        user = await UserCRUD.get_by_telegram_id(session, query.from_user.id)

        # Check admin rights
        if not user or not user.is_admin:
            await query.answer("❌ Доступ запрещен.", show_alert=True)
            return

        # Get all active votings instead of just one
        active_votings = await VotingCRUD.get_active(session)

        if not active_votings:
            await query.answer("❌ Нет активных голосований.", show_alert=True)
            return

        # Process each active voting
        all_voting_results = []
        for voting in active_votings:
            # Get results
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

            options = json.loads(voting.options) if isinstance(voting.options, str) else voting.options
            all_voting_results.append({
                'voting': voting,
                'options': options,
                'results': results,
                'total_votes': total_votes
            })

        # Export all results to a single Excel file on Yandex Disk
        sheets_url = None
        try:
            logger.info(f"Exporting {len(all_voting_results)} voting results to Yandex Disk...")
            sheets_url = await yandex_disk_service.export_all_voting_results(all_voting_results)
            if sheets_url:
                logger.info(f"Successfully exported voting results to: {sheets_url}")
            else:
                logger.warning("Export returned None - no URL was generated")
        except Exception as e:
            logger.error(f"Failed to export voting results: {e}", exc_info=True)

        # Send results to all verified users
        verified_users = await UserCRUD.get_all_verified(session)
        sent_count = 0
        for u in verified_users:
            if u.notifications_enabled:
                try:
                    # Prepare message with all voting results
                    message = f"📊 *Голосование завершено*\n\n"
                    message += f"Завершено вопросов: {len(all_voting_results)}\n\n"

                    for idx, result_data in enumerate(all_voting_results, 1):
                        voting = result_data['voting']
                        options = result_data['options']
                        results = result_data['results']
                        total_votes = result_data['total_votes']

                        message += f"*Вопрос {idx}: {voting.title}*\n"
                        message += f"Всего голосов: {total_votes}\n"
                        message += "*Результаты:*\n"

                        for i, option in enumerate(options):
                            votes = results.get(i, 0)
                            percent = (votes / total_votes * 100) if total_votes > 0 else 0
                            message += f"  {i+1}. {option}: {votes} ({percent:.1f}%)\n"
                        message += "\n"

                    # Add detailed results link only for admins
                    if u.is_admin and sheets_url:
                        message += f"\n📄 [Просмотреть детальные результаты]({sheets_url})"

                    await context.bot.send_message(
                        chat_id=u.telegram_id,
                        text=message,
                        parse_mode='Markdown'
                    )
                    sent_count += 1
                    await asyncio.sleep(0.1)
                except Exception as e:
                    logger.error(f"Failed to send results to {u.telegram_id}: {e}")

        await query.answer(f"✅ Голосование завершено. {len(all_voting_results)} вопросов завершено. Результаты отправлены {sent_count} пользователям.", show_alert=True)

        # Update admin's message to show completed status with detailed results link
        admin_message = f"📊 *Голосование завершено*\n\n"
        admin_message += f"Завершено вопросов: {len(all_voting_results)}\n\n"

        for idx, result_data in enumerate(all_voting_results, 1):
            voting = result_data['voting']
            options = result_data['options']
            results = result_data['results']
            total_votes = result_data['total_votes']

            admin_message += f"*Вопрос {idx}: {voting.title}*\n"
            admin_message += f"Всего голосов: {total_votes}\n"
            admin_message += "*Результаты:*\n"

            for i, option in enumerate(options):
                votes = results.get(i, 0)
                percent = (votes / total_votes * 100) if total_votes > 0 else 0
                admin_message += f"  {i+1}. {option}: {votes} ({percent:.1f}%)\n"
            admin_message += "\n"

        if sheets_url:
            admin_message += f"\n📄 [Просмотреть детальные результаты]({sheets_url})"

        try:
            await query.edit_message_text(admin_message, parse_mode='Markdown')
        except Exception as e:
            logger.error(f"Failed to update admin message: {e}", exc_info=True)
            # Try without markdown links if it fails
            try:
                if sheets_url:
                    admin_message_plain = admin_message.replace(f"[Просмотреть детальные результаты]({sheets_url})", f"Ссылка: {sheets_url}")
                    await query.edit_message_text(admin_message_plain, parse_mode='Markdown')
                else:
                    await query.edit_message_text(admin_message, parse_mode='Markdown')
            except Exception as e2:
                logger.error(f"Failed to update admin message even without links: {e2}", exc_info=True)


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
        "Шаг 1/2: Введите название голосования:",
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
        "Шаг 2/2: Введите описание голосования:\n\n"
        "Варианты ответа будут автоматически установлены: ЗА / ПРОТИВ"
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
    # Set fixed options: ЗА and ПРОТИВ
    context.user_data['voting_options'] = ["ЗА", "ПРОТИВ"]

    # Create voting immediately without setting end date
    async with async_session_maker() as session:
        user = await UserCRUD.get_by_telegram_id(session, update.effective_user.id)

        starts_at = datetime.utcnow()
        # Set far future date (will be closed manually by admin)
        ends_at = datetime.utcnow() + timedelta(days=365)

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
        "✅ Голосование создано и активировано!\n\n"
        f"*{voting.title}*\n\n"
        f"{voting.description[:200]}{'...' if len(voting.description) > 200 else ''}\n\n"
        "Варианты: ЗА / ПРОТИВ\n\n"
        "Голосование будет открыто до тех пор, пока администратор не закроет его вручную.",
        parse_mode='Markdown'
    )

    # Notify all verified users about new voting
    async with async_session_maker() as session:
        all_users = await UserCRUD.get_all_verified(session)

        for member in all_users:
            if member.notifications_enabled and member.telegram_id != update.effective_user.id:
                try:
                    await context.bot.send_message(
                        chat_id=member.telegram_id,
                        text=f"🔔 Новое голосование!\n\n"
                             f"*{voting.title}*\n\n"
                             f"{voting.description[:200]}{'...' if len(voting.description) > 200 else ''}\n\n"
                             f"Перейдите в раздел 'Голосования' для участия.",
                        parse_mode='Markdown'
                    )
                except Exception:
                    pass

    context.user_data.clear()
    return ConversationHandler.END


# Function removed - voting options are now fixed as "ЗА" and "ПРОТИВ"


# Function removed - voting duration is no longer needed, votings are closed manually by admin


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
        "Введите текст вопроса:\n\n"
        "Варианты ответа будут автоматически установлены: ЗА / ПРОТИВ",
        parse_mode='Markdown'
    )
    return PROPOSE_DESCRIPTION


async def propose_receive_description(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Receive proposed question description"""
    description = update.message.text.strip()

    if not validate_description(description):
        await update.message.reply_text(
            "❌ Текст вопроса должен быть от 10 до 4000 символов. Попробуйте еще раз:"
        )
        return PROPOSE_DESCRIPTION

    context.user_data['propose_description'] = description

    # Set fixed options and create draft voting immediately
    options = ["ЗА", "ПРОТИВ"]

    # Get user info first
    async with async_session_maker() as session:
        user = await UserCRUD.get_by_telegram_id(session, update.effective_user.id)
        user_display_name = get_user_display_name(user)

        # Use description as title (first 100 chars) since we removed title step
        title = description[:100] + ('...' if len(description) > 100 else '')

        # Create draft voting (not active yet)
        voting = await VotingCRUD.create(
            session,
            title=title,
            description=description,
            options=json.dumps(options),
            creator_id=user.id,
            status=VotingStatus.DRAFT,
            starts_at=datetime.utcnow(),
            ends_at=datetime.utcnow() + timedelta(days=config.VOTE_DURATION_DAYS),
            quorum_percent=config.DEFAULT_QUORUM_PERCENT
        )

    await update.message.reply_text(
        f"✅ Вопрос предложен!\n\n"
        f"{voting.description[:200]}{'...' if len(voting.description) > 200 else ''}\n\n"
        f"Варианты ответа: ЗА / ПРОТИВ\n\n"
        "Ваш вопрос отправлен на модерацию администраторам.\n"
        "После одобрения он будет опубликован для всех участников."
    )

    # Notify admins about new proposed question
    async with async_session_maker() as session:
        # Get all users and filter admins (admins can have any status)
        from database.models import User
        from sqlalchemy import select
        result = await session.execute(select(User).where(User.is_admin == True))
        admin_users = result.scalars().all()

        for admin in admin_users:
            try:
                await context.bot.send_message(
                    chat_id=admin.telegram_id,
                    text=f"🔔 Новый вопрос для голосования!\n\n"
                         f"От: {user_display_name}\n"
                         f"Вопрос: {voting.description[:200]}{'...' if len(voting.description) > 200 else ''}\n\n"
                         f"Используйте /admin для просмотра и одобрения."
                )
            except Exception as e:
                logger.error(f"Failed to notify admin {admin.telegram_id}: {e}")

    context.user_data.clear()
    return ConversationHandler.END


# Function removed - voting options are now fixed as "ЗА" and "ПРОТИВ"


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
    application.add_handler(CallbackQueryHandler(voting_menu_callback, pattern="^voting_menu$"))
    application.add_handler(CallbackQueryHandler(voting_list_callback, pattern="^voting_list$"))
    application.add_handler(CallbackQueryHandler(voting_view_callback, pattern="^voting_view_"))
    application.add_handler(CallbackQueryHandler(vote_cast_callback, pattern="^vote_cast_"))
    application.add_handler(CallbackQueryHandler(vote_revote_callback, pattern="^vote_revote_"))
    application.add_handler(CallbackQueryHandler(vote_recast_callback, pattern="^vote_recast_"))
    application.add_handler(CallbackQueryHandler(voting_end_callback, pattern="^voting_end_"))
    application.add_handler(CallbackQueryHandler(voting_create_start, pattern="^voting_create$"))
    # Removed: voting_my and voting_history - not needed by users
    # application.add_handler(CallbackQueryHandler(voting_my_callback, pattern="^voting_my$"))
    # application.add_handler(CallbackQueryHandler(voting_history_callback, pattern="^voting_history$"))
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
            PROPOSE_DESCRIPTION: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, propose_receive_description)
            ],
        },
        fallbacks=[],
        allow_reentry=True,
        per_chat=True
    )
    application.add_handler(propose_voting_conv)
