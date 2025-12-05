# Настройка интеграции с Google Sheets

Интеграция с Google Sheets позволяет автоматически экспортировать результаты голосований в Google таблицы для удобного просмотра и анализа.

## Шаг 1: Создание проекта в Google Cloud Console

1. Перейдите в [Google Cloud Console](https://console.cloud.google.com/)
2. Создайте новый проект или выберите существующий
3. Назовите проект, например "Lazurny Bot"

## Шаг 2: Включение API

1. В меню навигации выберите **APIs & Services** > **Library**
2. Найдите и включите следующие API:
   - **Google Sheets API**
   - **Google Drive API**

## Шаг 3: Создание Service Account

1. Перейдите в **APIs & Services** > **Credentials**
2. Нажмите **Create Credentials** > **Service Account**
3. Заполните данные:
   - **Service account name**: `lazurny-bot-sheets`
   - **Service account ID**: будет создан автоматически
   - **Description**: "Service account for Lazurny Bot Google Sheets integration"
4. Нажмите **Create and Continue**
5. Роли не требуются, нажмите **Continue**
6. Нажмите **Done**

## Шаг 4: Создание ключа

1. В списке Service Accounts найдите созданный аккаунт
2. Нажмите на него, перейдите на вкладку **Keys**
3. Нажмите **Add Key** > **Create new key**
4. Выберите формат **JSON**
5. Нажмите **Create**
6. JSON файл с учетными данными будет скачан на ваш компьютер

## Шаг 5: Установка credentials в проект

1. Переименуйте скачанный файл в `credentials.json`
2. Поместите файл в корневую директорию проекта:
   ```
   lazurny_bot/
   ├── credentials.json  ← здесь
   ├── bot.py
   ├── .env
   └── ...
   ```

## Шаг 6: Добавление в .gitignore

**ВАЖНО**: Убедитесь, что `credentials.json` добавлен в `.gitignore`:

```gitignore
# Google Sheets credentials
credentials.json
```

## Шаг 7: Установка зависимостей

Зависимости уже добавлены в `requirements.txt`. Установите их:

```bash
pip install -r requirements.txt
```

Или в Docker:
```bash
docker-compose build
docker-compose up -d
```

## Использование

После настройки интеграция работает автоматически:

1. При завершении голосования результаты автоматически экспортируются в новую Google таблицу
2. Таблица становится общедоступной для чтения (только чтение)
3. Ссылка на таблицу отправляется всем пользователям вместе с результатами

### Формат таблицы

Экспортированная таблица содержит:
- Название и описание голосования
- ID голосования и даты создания/завершения
- Общее количество голосов
- Детальные результаты по каждому варианту (количество и процент)

### Доступ к таблицам

Все созданные таблицы доступны в Google Drive аккаунта Service Account:

1. Скопируйте email Service Account из файла `credentials.json` (поле `client_email`)
2. Он будет выглядеть примерно так: `lazurny-bot-sheets@project-id.iam.gserviceaccount.com`
3. Войдите в Google Drive с этим аккаунтом для просмотра всех созданных таблиц

## Проверка работоспособности

Чтобы проверить работу интеграции:

1. Создайте тестовое голосование через админ-панель
2. Дождитесь завершения голосования (или измените время завершения в БД)
3. При завершении голосования проверьте логи бота:
   ```bash
   docker logs lazurny_bot
   ```
4. Найдите строку: `Voting results exported to Google Sheets: https://...`
5. Перейдите по ссылке - должна открыться таблица с результатами

## Устранение неполадок

### Ошибка: "gspread not installed"
Установите зависимости: `pip install -r requirements.txt`

### Ошибка: "Failed to initialize Google Sheets client"
- Проверьте, что файл `credentials.json` находится в корневой директории проекта
- Убедитесь, что файл содержит корректный JSON
- Проверьте, что Google Sheets API и Google Drive API включены в проекте

### Ошибка: "Failed to create spreadsheet"
- Убедитесь, что Service Account имеет доступ к Google Drive
- Проверьте квоты API в Google Cloud Console

### Таблица создается, но ссылка недоступна
- Проверьте настройки публичного доступа
- Убедитесь, что у Service Account есть права на создание файлов

## Отключение интеграции

Если вы не хотите использовать Google Sheets:

1. Просто не создавайте файл `credentials.json`
2. Бот будет работать в обычном режиме, но без экспорта в таблицы
3. В логах появится предупреждение: `Google Sheets not available, skipping export`

## Безопасность

⚠️ **ВАЖНО**:
- **НЕ** публикуйте файл `credentials.json` в открытом доступе
- **НЕ** коммитьте его в Git
- Храните резервную копию в надежном месте
- При компрометации ключа - удалите его в Google Cloud Console и создайте новый
