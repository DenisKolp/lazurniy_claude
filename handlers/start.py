"""
Start command and user verification handlers
"""
from telegram import Update, ReplyKeyboardMarkup, KeyboardButton, InlineKeyboardMarkup, InlineKeyboardButton
from telegram.ext import (
    ContextTypes, CommandHandler, MessageHandler,
    filters, ConversationHandler, CallbackQueryHandler
)
from database.crud import UserCRUD
from database.models import UserStatus
from database.session import async_session_maker
from utils.validators import validate_phone_number, validate_document, validate_address
from config import config


# Conversation states
FULL_NAME, PHONE_NUMBER, DOCUMENTS, ADDRESS = range(4)


async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /start command"""
    async with async_session_maker() as session:
        user = await UserCRUD.get_by_telegram_id(session, update.effective_user.id)

        if user:
            if user.status == UserStatus.VERIFIED:
                await show_main_menu(update, context)
            elif user.status == UserStatus.PENDING:
                keyboard = [
                    [KeyboardButton("ℹ️ Информация"), KeyboardButton("❓ Помощь")],
                    [KeyboardButton("🔒 Политика конфиденциальности")],
                    [KeyboardButton("🏠 Старт")]
                ]
                reply_markup = ReplyKeyboardMarkup(keyboard, resize_keyboard=True)

                await update.message.reply_text(
                    "⏳ Ваша заявка на верификацию находится на рассмотрении.\n"
                    "Пожалуйста, дождитесь одобрения администратором.",
                    reply_markup=reply_markup
                )
            elif user.status == UserStatus.REJECTED:
                # Show same welcome message as for new users
                keyboard = [
                    [KeyboardButton("🔐 Пройти верификацию")],
                    [KeyboardButton("ℹ️ Информация"), KeyboardButton("❓ Помощь")],
                    [KeyboardButton("🔒 Политика конфиденциальности")],
                    [KeyboardButton("🏠 Старт")]
                ]
                reply_markup = ReplyKeyboardMarkup(keyboard, resize_keyboard=True)

                await update.message.reply_text(
                    "👋 Добро пожаловать чат-бот КП 'Лазурный'!\n\n"
                    "Для начала работы необходимо пройти верификацию.\n\n"
                    "🔒 *Конфиденциальность данных*\n"
                    "Нажимая кнопку '🔐 Пройти верификацию', вы соглашаетесь с обработкой ваших персональных данных "
                    "в соответствии с нашей Политикой конфиденциальности.\n\n"
                    "Нажмите кнопку 'Политика конфиденциальности' для просмотра полной политики.",
                    reply_markup=reply_markup,
                    parse_mode='Markdown'
                )
        else:
            keyboard = [
                [KeyboardButton("🔐 Пройти верификацию")],
                [KeyboardButton("ℹ️ Информация"), KeyboardButton("❓ Помощь")],
                [KeyboardButton("🔒 Политика конфиденциальности")],
                [KeyboardButton("🏠 Старт")]
            ]
            reply_markup = ReplyKeyboardMarkup(keyboard, resize_keyboard=True)

            await update.message.reply_text(
                "👋 Добро пожаловать чат-бот КП 'Лазурный'!\n\n"
                "Для начала работы необходимо пройти верификацию.\n\n"
                "🔒 *Конфиденциальность данных*\n"
                "Нажимая кнопку '🔐 Пройти верификацию', вы соглашаетесь с обработкой ваших персональных данных "
                "в соответствии с нашей Политикой конфиденциальности.\n\n"
                "Нажмите кнопку 'Политика конфиденциальности' для просмотра полной политики.",
                reply_markup=reply_markup,
                parse_mode='Markdown'
            )


async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Show help information"""
    await update.message.reply_text(
        "❓ *Помощь*\n\n"
        "Если у вас возникли вопросы или проблемы, вы можете обратиться:\n\n"
        "📧 Email: i@deniskolp.ru\n"
        "📞 Телефон: +7 (XXX) XXX-XX-XX\n\n",
        parse_mode='Markdown'
    )


async def info_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Show information and useful links"""
    await update.message.reply_text(
        "ℹ️ *Информация*\n\n"
        "📋 *Полезные ссылки:*\n\n"
        "🌐 [Официальный сайт КП](https://lazurny-kp.ru)\n"
        "📱 [Группа ВКонтакте](https://vk.com/lazurny_kp)\n"
        "📸 [Instagram](https://instagram.com/lazurny_kp)\n"
        "📘 [Правила проживания](https://lazurny-kp.ru/rules)\n"
        "📄 [Документы](https://lazurny-kp.ru/documents)\n\n"
        "💡 *О системе:*\n"
        "Этот бот позволяет:\n"
        "• Участвовать в голосованиях\n"
        "• Получать уведомления о событиях\n"
        "• Подавать обращения в инициативную группу\n"
        "• Быть в курсе всех новостей КП\n\n"
        "🔒 Для просмотра политики конфиденциальности используйте /privacy",
        parse_mode='Markdown',
        disable_web_page_preview=True
    )


async def privacy_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Show privacy policy"""
    privacy_text = """🔒 ПОЛИТИКА КОНФИДЕНЦИАЛЬНОСТИ

1. Собираемые данные:
• Telegram ID
• ФИО
• Номер телефона
• Адрес участка в КП
• Username (если указан)
• Документы (по желанию)
• История голосований и обращений

2. Цели обработки:
• Верификация членов КП
• Организация голосований
• Уведомления о событиях
• Обработка обращений

3. Безопасность:
• Данные хранятся на защищенных серверах
• Доступ только у администраторов
• Шифрование при передаче
• Не передаем данные третьим лицам

4. Ваши права:
• Доступ к своим данным
• Исправление данных
• Удаление данных
• Отзыв согласия

5. Контакты:
Email: i@deniskolp.ru

Используя бот, вы соглашаетесь с условиями обработки персональных данных."""

    await update.message.reply_text(privacy_text)


async def verify_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Start verification process"""
    keyboard = [
        [KeyboardButton("❌ Отмена")]
    ]
    reply_markup = ReplyKeyboardMarkup(keyboard, resize_keyboard=True)

    await update.message.reply_text(
        "🔐 *Процесс верификации*\n\n"
        "👤 Шаг 1/4: ФИО\n\n"
        "Пожалуйста, введите ваше полное ФИО (Фамилия Имя Отчество):\n\n"
        "Пример: Иванов Иван Иванович",
        reply_markup=reply_markup,
        parse_mode='Markdown'
    )
    return FULL_NAME


async def receive_full_name(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Receive full name"""
    if update.message.text == "❌ Отмена":
        context.user_data.clear()

        keyboard = [
            [KeyboardButton("🔐 Пройти верификацию")],
            [KeyboardButton("ℹ️ Информация"), KeyboardButton("❓ Помощь")],
            [KeyboardButton("🔒 Политика конфиденциальности")],
            [KeyboardButton("🏠 Старт")]
        ]
        reply_markup = ReplyKeyboardMarkup(keyboard, resize_keyboard=True)

        await update.message.reply_text(
            "❌ Верификация отменена.\n\n"
            "Вы можете начать процесс верификации заново, нажав кнопку '🔐 Пройти верификацию'.",
            reply_markup=reply_markup
        )
        return ConversationHandler.END

    full_name = update.message.text.strip()

    # Validate full name (at least 2 words, 3-100 characters)
    if len(full_name) < 3 or len(full_name) > 100:
        await update.message.reply_text(
            "❌ ФИО должно содержать от 3 до 100 символов. Попробуйте еще раз:"
        )
        return FULL_NAME

    words = full_name.split()
    if len(words) < 2:
        await update.message.reply_text(
            "❌ Пожалуйста, введите полное ФИО (минимум Фамилия и Имя).\n\n"
            "Пример: Иванов Иван Иванович"
        )
        return FULL_NAME

    context.user_data['full_name'] = full_name

    keyboard = [
        [KeyboardButton("📱 Отправить номер телефона", request_contact=True)],
        [KeyboardButton("❌ Отмена")]
    ]
    reply_markup = ReplyKeyboardMarkup(keyboard, resize_keyboard=True, one_time_keyboard=True)

    await update.message.reply_text(
        "✅ ФИО сохранено!\n\n"
        "📱 Шаг 2/4: Подтверждение номера телефона\n\n"
        "Вы можете:\n"
        "• Нажать кнопку '📱 Отправить номер телефона' для автоматической отправки\n"
        "• Или ввести номер телефона вручную в любом формате:\n",
        reply_markup=reply_markup,
        parse_mode='Markdown'
    )
    return PHONE_NUMBER


async def receive_phone_number(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Receive phone number"""
    # Check for cancellation first
    if update.message.text and update.message.text == "❌ Отмена":
        context.user_data.clear()

        keyboard = [
            [KeyboardButton("🔐 Пройти верификацию")],
            [KeyboardButton("ℹ️ Информация"), KeyboardButton("❓ Помощь")],
            [KeyboardButton("🔒 Политика конфиденциальности")],
            [KeyboardButton("🏠 Старт")]
        ]
        reply_markup = ReplyKeyboardMarkup(keyboard, resize_keyboard=True)

        await update.message.reply_text(
            "❌ Верификация отменена.\n\n"
            "Вы можете начать процесс верификации заново, нажав кнопку '🔐 Пройти верификацию'.",
            reply_markup=reply_markup
        )
        return ConversationHandler.END

    # Handle contact (button press)
    if update.message.contact:
        phone = update.message.contact.phone_number
        validated_phone = validate_phone_number(phone)

        if validated_phone:
            context.user_data['phone_number'] = validated_phone

            keyboard = [
                [KeyboardButton("⏭️ Пропустить загрузку документов")],
                [KeyboardButton("❌ Отмена")]
            ]
            reply_markup = ReplyKeyboardMarkup(keyboard, resize_keyboard=True)

            await update.message.reply_text(
                "✅ Номер телефона принят!\n\n"
                "📄 Шаг 3/4: Загрузка документов\n\n"
                "Пожалуйста, загрузите любые документы, подтверждающие ваше право собственности:\n"
                "- Свидетельство о собственности\n"
                "- Договор купли-продажи\n"
                "- Фотографии документов\n\n"
                "Принимаются форматы: PDF, JPG, PNG\n\n"
                "Вы можете загрузить несколько документов или пропустить этот шаг.",
                reply_markup=reply_markup
            )
            return DOCUMENTS
        else:
            await update.message.reply_text(
                "❌ Некорректный номер телефона. Попробуйте еще раз."
            )
            return PHONE_NUMBER

    # Handle text input (manual phone number entry)
    elif update.message.text:
        phone = update.message.text.strip()
        validated_phone = validate_phone_number(phone)

        if validated_phone:
            context.user_data['phone_number'] = validated_phone

            keyboard = [
                [KeyboardButton("⏭️ Пропустить загрузку документов")],
                [KeyboardButton("❌ Отмена")]
            ]
            reply_markup = ReplyKeyboardMarkup(keyboard, resize_keyboard=True)

            await update.message.reply_text(
                "✅ Номер телефона принят!\n\n"
                "📄 Шаг 3/4: Загрузка документов\n\n"
                "Пожалуйста, загрузите любые документы, подтверждающие ваше право собственности:\n"
                "- Свидетельство о собственности\n"
                "- Договор купли-продажи\n"
                "- Фотографии документов\n\n"
                "Принимаются форматы: PDF, JPG, PNG\n\n"
                "Вы можете загрузить несколько документов или пропустить этот шаг.",
                reply_markup=reply_markup
            )
            return DOCUMENTS
        else:
            await update.message.reply_text(
                "❌ Некорректный формат номера телефона.\n\n"
                "Попробуйте еще раз. Принимаются форматы:\n"
                "• +7 (XXX) XXX-XX-XX\n"
                "• +7XXXXXXXXXX\n"
                "• 8XXXXXXXXXX\n\n"
                "Или нажмите кнопку '📱 Отправить номер телефона'"
            )
            return PHONE_NUMBER

    else:
        await update.message.reply_text(
            "❌ Пожалуйста, отправьте номер телефона текстом или используйте кнопку."
        )
        return PHONE_NUMBER


async def receive_documents(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Receive verification documents"""
    # Handle photo
    if update.message.photo:
        # Get the largest photo
        photo = update.message.photo[-1]
        if 'documents' not in context.user_data:
            context.user_data['documents'] = []
        # Store file_id with type information
        context.user_data['documents'].append({
            'file_id': photo.file_id,
            'type': 'photo'
        })

        keyboard = [
            [KeyboardButton("✅ Готово, перейти к следующему шагу")],
            [KeyboardButton("➕ Загрузить еще документ")],
            [KeyboardButton("❌ Отмена")]
        ]
        reply_markup = ReplyKeyboardMarkup(keyboard, resize_keyboard=True)

        await update.message.reply_text(
            f"✅ Фото получено!\n\n"
            f"Загружено документов: {len(context.user_data['documents'])}",
            reply_markup=reply_markup
        )
        return DOCUMENTS

    # Handle document
    elif update.message.document:
        file = update.message.document
        if validate_document(file.file_name):
            # Store file_id with type information
            if 'documents' not in context.user_data:
                context.user_data['documents'] = []
            context.user_data['documents'].append({
                'file_id': file.file_id,
                'type': 'document'
            })

            keyboard = [
                [KeyboardButton("✅ Готово, перейти к следующему шагу")],
                [KeyboardButton("➕ Загрузить еще документ")],
                [KeyboardButton("❌ Отмена")]
            ]
            reply_markup = ReplyKeyboardMarkup(keyboard, resize_keyboard=True)

            await update.message.reply_text(
                f"✅ Документ '{file.file_name}' получен!\n\n"
                f"Загружено документов: {len(context.user_data['documents'])}",
                reply_markup=reply_markup
            )
            return DOCUMENTS
        else:
            await update.message.reply_text(
                "❌ Неподдерживаемый формат файла.\n"
                "Пожалуйста, загрузите PDF, JPG или PNG файл."
            )
            return DOCUMENTS

    elif update.message.text == "⏭️ Пропустить загрузку документов":
        # Skip documents - set empty list
        context.user_data['documents'] = []

        keyboard = [
            [KeyboardButton("❌ Отмена")]
        ]
        reply_markup = ReplyKeyboardMarkup(keyboard, resize_keyboard=True)

        await update.message.reply_text(
            "⏭️ Загрузка документов пропущена.\n\n"
            "📍 Шаг 4/4: Адрес участка\n\n"
            "Пожалуйста, введите номер вашего участка или адрес в КП 'Лазурный'.\n\n"
            "Примеры:\n"
            "• Лазурная 173\n"
            "• Лазурная 173/1",
            reply_markup=reply_markup
        )
        return ADDRESS

    elif update.message.text == "✅ Готово, перейти к следующему шагу":
        if 'documents' in context.user_data and context.user_data['documents']:
            keyboard = [
                [KeyboardButton("❌ Отмена")]
            ]
            reply_markup = ReplyKeyboardMarkup(keyboard, resize_keyboard=True)

            await update.message.reply_text(
                "📍 Шаг 4/4: Адрес участка\n\n"
                "Пожалуйста, введите номер вашего участка или адрес в КП 'Лазурный'.\n\n"
                "Примеры:\n"
                "• Лазурная 173\n"
                "• Лазурная 173/1",
                reply_markup=reply_markup
            )
            return ADDRESS
        else:
            await update.message.reply_text(
                "Пожалуйста, загрузите хотя бы один документ или нажмите 'Пропустить'."
            )
            return DOCUMENTS

    elif update.message.text == "➕ Загрузить еще документ":
        keyboard = [
            [KeyboardButton("❌ Отмена")]
        ]
        reply_markup = ReplyKeyboardMarkup(keyboard, resize_keyboard=True)

        await update.message.reply_text(
            "📎 Загрузите следующий документ или фото:",
            reply_markup=reply_markup
        )
        return DOCUMENTS

    elif update.message.text == "❌ Отмена":
        context.user_data.clear()

        keyboard = [
            [KeyboardButton("🔐 Пройти верификацию")],
            [KeyboardButton("ℹ️ Информация"), KeyboardButton("❓ Помощь")],
            [KeyboardButton("🔒 Политика конфиденциальности")],
            [KeyboardButton("🏠 Старт")]
        ]
        reply_markup = ReplyKeyboardMarkup(keyboard, resize_keyboard=True)

        await update.message.reply_text(
            "❌ Верификация отменена.\n\n"
            "Вы можете начать процесс верификации заново, нажав кнопку '🔐 Пройти верификацию'.",
            reply_markup=reply_markup
        )
        return ConversationHandler.END

    else:
        await update.message.reply_text(
            "Пожалуйста, загрузите документ или используйте кнопки меню."
        )
        return DOCUMENTS


async def receive_address(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Receive address and complete verification"""
    if update.message.text == "❌ Отмена":
        context.user_data.clear()

        keyboard = [
            [KeyboardButton("🔐 Пройти верификацию")],
            [KeyboardButton("ℹ️ Информация"), KeyboardButton("❓ Помощь")],
            [KeyboardButton("🔒 Политика конфиденциальности")],
            [KeyboardButton("🏠 Старт")]
        ]
        reply_markup = ReplyKeyboardMarkup(keyboard, resize_keyboard=True)

        await update.message.reply_text(
            "❌ Верификация отменена.\n\n"
            "Вы можете начать процесс верификации заново, нажав кнопку '🔐 Пройти верификацию'.",
            reply_markup=reply_markup
        )
        return ConversationHandler.END

    address = update.message.text.strip()
    validated_address = validate_address(address)

    if not validated_address:
        await update.message.reply_text(
            "❌ Некорректный формат адреса.\n\n"
            "Пожалуйста, введите адрес в одном из следующих форматов:\n"
            "• Лазурная 173\n"
            "• Лазурная 173/1"
        )
        return ADDRESS

    context.user_data['address'] = validated_address

    # Create user in database
    async with async_session_maker() as session:
        user = await UserCRUD.get_by_telegram_id(session, update.effective_user.id)

        import json
        user_data = {
            'username': update.effective_user.username,
            'first_name': update.effective_user.first_name,
            'last_name': update.effective_user.last_name,
            'full_name': context.user_data['full_name'],
            'phone_number': context.user_data['phone_number'],
            'address': context.user_data['address'],
            'verification_documents': json.dumps(context.user_data['documents']),
            'status': UserStatus.PENDING
        }

        if user:
            await UserCRUD.update(session, user, **user_data)
        else:
            await UserCRUD.create(
                session,
                telegram_id=update.effective_user.id,
                **user_data
            )

    # Notify admins
    for admin_id in config.ADMIN_IDS:
        try:
            await context.bot.send_message(
                chat_id=admin_id,
                text=f"🔔 Новая заявка на верификацию!\n\n"
                     f"ФИО: {context.user_data['full_name']}\n"
                     f"Username: @{update.effective_user.username or 'N/A'}\n"
                     f"Телефон: {context.user_data['phone_number']}\n"
                     f"Адрес: {validated_address}\n\n"
                     f"Используйте /admin для просмотра заявок."
            )
        except Exception:
            pass

    # Show success message with button to return to start menu
    keyboard = [
        [KeyboardButton("ℹ️ Информация"), KeyboardButton("❓ Помощь")],
        [KeyboardButton("🔒 Политика конфиденциальности")],
        [KeyboardButton("🏠 Старт")]
    ]
    reply_markup = ReplyKeyboardMarkup(keyboard, resize_keyboard=True)

    await update.message.reply_text(
        "✅ Заявка на верификацию успешно отправлена!\n\n"
        "Администратор рассмотрит вашу заявку в ближайшее время.\n"
        "Вы получите уведомление о результатах проверки.",
        reply_markup=reply_markup
    )

    # Clear user data
    context.user_data.clear()

    return ConversationHandler.END


async def cancel_verification(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Cancel verification"""
    context.user_data.clear()

    # Show menu with verification button
    keyboard = [
        [KeyboardButton("🔐 Пройти верификацию")],
        [KeyboardButton("ℹ️ Информация"), KeyboardButton("❓ Помощь")],
        [KeyboardButton("🔒 Политика конфиденциальности")],
        [KeyboardButton("🏠 Старт")]
    ]
    reply_markup = ReplyKeyboardMarkup(keyboard, resize_keyboard=True)

    await update.message.reply_text(
        "❌ Верификация отменена.\n\n"
        "Вы можете начать процесс верификации заново, нажав кнопку '🔐 Пройти верификацию'.",
        reply_markup=reply_markup
    )
    return ConversationHandler.END


async def settings_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Show settings menu"""
    async with async_session_maker() as session:
        user = await UserCRUD.get_by_telegram_id(session, update.effective_user.id)

        if not user or user.status != UserStatus.VERIFIED:
            await update.message.reply_text(
                "❌ Доступ запрещен. Пройдите верификацию."
            )
            return

        keyboard = [
            [InlineKeyboardButton(
                f"🔔 Уведомления: {'✅ Вкл' if user.notifications_enabled else '❌ Выкл'}",
                callback_data=f"settings_notifications_{'off' if user.notifications_enabled else 'on'}"
            )],
            [InlineKeyboardButton("◀️ Назад в меню", callback_data="settings_back")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)

        await update.message.reply_text(
            "⚙️ *Настройки*\n\n"
            "Управляйте своими предпочтениями:",
            reply_markup=reply_markup,
            parse_mode='Markdown'
        )


async def settings_notifications_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Toggle notifications"""
    query = update.callback_query
    await query.answer()

    action = query.data.split("_")[-1]
    enable = action == "on"

    async with async_session_maker() as session:
        user = await UserCRUD.get_by_telegram_id(session, update.effective_user.id)
        if user:
            await UserCRUD.update(session, user, notifications_enabled=enable)

        keyboard = [
            [InlineKeyboardButton(
                f"🔔 Уведомления: {'✅ Вкл' if enable else '❌ Выкл'}",
                callback_data=f"settings_notifications_{'off' if enable else 'on'}"
            )],
            [InlineKeyboardButton("◀️ Назад в меню", callback_data="settings_back")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)

        await query.edit_message_text(
            "⚙️ *Настройки*\n\n"
            "Управляйте своими предпочтениями:",
            reply_markup=reply_markup,
            parse_mode='Markdown'
        )


async def settings_back_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Go back to main menu from settings"""
    query = update.callback_query
    await query.answer()

    await query.delete_message()
    # Recreate the update object to call start_command
    update.message = update.effective_message
    await show_main_menu(update, context)


async def show_main_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Show main menu for association members"""
    keyboard = [
        [KeyboardButton("🗳️ Голосования"), KeyboardButton("📅 События")],
        [KeyboardButton("📝 Обращение в ИГ"), KeyboardButton("⚙️ Настройки")],
    ]

    async with async_session_maker() as session:
        user = await UserCRUD.get_by_telegram_id(session, update.effective_user.id)
        if user and user.is_admin:
            keyboard.append([KeyboardButton("👨‍💼 Админ-панель")])

    reply_markup = ReplyKeyboardMarkup(keyboard, resize_keyboard=True)

    welcome_message = (
        f"👋 Добро пожаловать, {update.effective_user.first_name}!\n\n"
        "🏘️ *Чат-бот КП 'Лазурный'*\n\n"
        "Этот бот создан для удобного взаимодействия жителей коттеджного поселка и помогает:\n\n"
        "🗳️ *Голосования*\n"
        "• Участвуйте в общих голосованиях по важным вопросам\n"
        "• Инициируйте свои предложения для голосования\n"
        "• Отслеживайте результаты в реальном времени\n\n"
        "📅 *События*\n"
        "• Будьте в курсе всех мероприятий поселка\n"
        "• Получайте напоминания о важных событиях\n"
        "• Просматривайте календарь событий\n\n"
        "📝 *Обращения*\n"
        "• Отправляйте заявки в инициативную группу\n"
        "• Сообщайте о проблемах и предложениях\n"
        "• Отслеживайте статус своих обращений\n\n"
        "⚙️ *Настройки*\n"
        "• Управляйте уведомлениями\n"
        "• Настраивайте параметры под себя\n\n"
        "Выберите нужный раздел из меню ниже 👇"
    )

    await update.message.reply_text(
        welcome_message,
        reply_markup=reply_markup,
        parse_mode='Markdown'
    )


async def handle_any_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle any message from users not in the system"""
    # Check if user exists in database
    async with async_session_maker() as session:
        user = await UserCRUD.get_by_telegram_id(session, update.effective_user.id)

    # If user doesn't exist, show start message
    if not user:
        keyboard = [
            [KeyboardButton("🔐 Пройти верификацию")],
            [KeyboardButton("ℹ️ Информация"), KeyboardButton("❓ Помощь")],
            [KeyboardButton("🔒 Политика конфиденциальности")],
            [KeyboardButton("🏠 Старт")]
        ]
        reply_markup = ReplyKeyboardMarkup(keyboard, resize_keyboard=True)

        await update.message.reply_text(
            "👋 Добро пожаловать чат-бот КП 'Лазурный'!\n\n"
                "Для начала работы необходимо пройти верификацию.\n\n"
                "🔒 *Конфиденциальность данных*\n"
                "Нажимая кнопку '🔐 Пройти верификацию', вы соглашаетесь с обработкой ваших персональных данных "
                "в соответствии с нашей Политикой конфиденциальности.\n\n"
                "Нажмите кнопку 'Политика конфиденциальности' для просмотра полной политики.",
            reply_markup=reply_markup,
            parse_mode='Markdown'
        )


def register_start_handlers(application):
    """Register start and verification handlers"""
    # Start command and button
    application.add_handler(CommandHandler("start", start_command))
    application.add_handler(MessageHandler(filters.Regex("^🏠 Старт$"), start_command))

    # Help, info and privacy
    application.add_handler(CommandHandler("privacy", privacy_command))
    application.add_handler(MessageHandler(filters.Regex("^🔒 Политика конфиденциальности$"), privacy_command))
    application.add_handler(MessageHandler(filters.Regex("^❓ Помощь$"), help_command))
    application.add_handler(MessageHandler(filters.Regex("^ℹ️ Информация$"), info_command))

    # Settings
    application.add_handler(MessageHandler(filters.Regex("^⚙️ Настройки$"), settings_menu))
    application.add_handler(CallbackQueryHandler(settings_notifications_callback, pattern="^settings_notifications_"))
    application.add_handler(CallbackQueryHandler(settings_back_callback, pattern="^settings_back$"))

    # Verification conversation
    verification_conv = ConversationHandler(
        entry_points=[
            CommandHandler("verify", verify_start),
            MessageHandler(filters.Regex("^🔐 Пройти верификацию$"), verify_start)
        ],
        states={
            FULL_NAME: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, receive_full_name)
            ],
            PHONE_NUMBER: [
                MessageHandler(filters.CONTACT | filters.TEXT, receive_phone_number)
            ],
            DOCUMENTS: [
                MessageHandler(filters.PHOTO, receive_documents),
                MessageHandler(filters.Document.ALL, receive_documents),
                MessageHandler(filters.TEXT & ~filters.COMMAND, receive_documents)
            ],
            ADDRESS: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, receive_address)
            ],
        },
        fallbacks=[CommandHandler("cancel", cancel_verification)],
    )
    application.add_handler(verification_conv)

    # Catch-all handler for any message from new users (must be last!)
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_any_message))
