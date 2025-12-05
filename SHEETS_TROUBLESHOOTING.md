# Решение проблемы с Google Sheets

## Проблема
Бот не создает таблицу реестра в Google Sheets при одобрении пользователей.

## Возможные причины

### 1. Библиотеки не установлены

Проверьте, установлены ли необходимые библиотеки:

```bash
pip install gspread oauth2client
```

Или установите все зависимости:

```bash
pip install -r requirements.txt
```

### 2. Файл credentials.json некорректный

Файл `credentials.json` должен содержать корректные данные Service Account из Google Cloud Console.

**Проверьте структуру файла:**
```json
{
  "type": "service_account",
  "project_id": "your-project-id",
  "private_key_id": "...",
  "private_key": "-----BEGIN PRIVATE KEY-----\n...\n-----END PRIVATE KEY-----\n",
  "client_email": "your-service-account@your-project.iam.gserviceaccount.com",
  "client_id": "...",
  "auth_uri": "https://accounts.google.com/o/oauth2/auth",
  "token_uri": "https://oauth2.googleapis.com/token",
  "auth_provider_x509_cert_url": "https://www.googleapis.com/oauth2/v1/certs",
  "client_x509_cert_url": "..."
}
```

### 3. Google Sheets API не включен

В Google Cloud Console нужно включить **Google Sheets API** и **Google Drive API**:

1. Перейдите в [Google Cloud Console](https://console.cloud.google.com/)
2. Выберите ваш проект
3. **APIs & Services** → **Library**
4. Найдите и включите:
   - **Google Sheets API**
   - **Google Drive API**

### 4. Service Account не имеет прав

Убедитесь, что Service Account создан правильно и имеет права на создание файлов в Google Drive.

## Как проверить, работает ли интеграция

### Способ 1: Запустить тестовый скрипт

Запустите `test_sheets.py`:

```bash
python test_sheets.py
```

Этот скрипт:
1. Проверит установку библиотек
2. Проверит наличие credentials.json
3. Попытается создать тестовую таблицу
4. Выведет ссылку на созданную таблицу

### Способ 2: Проверить логи бота

При запуске бота в логах должно быть:

```
Google Sheets service initialized successfully
```

Если вместо этого:

```
gspread or oauth2client not installed. Google Sheets integration disabled.
```

Значит библиотеки не установлены.

Если:

```
Failed to initialize Google Sheets client: [error message]
```

Значит проблема с credentials.json или API не включены.

### Способ 3: Проверить при одобрении пользователя

1. Запустите бота
2. Одобрите заявку пользователя через админ-панель
3. В логах должно появиться:

```
Registry exported to Google Sheets: https://docs.google.com/spreadsheets/d/...
```

Если этого нет, значит произошла ошибка. Проверьте логи на наличие:

```
Failed to export registry: [error message]
```

## Быстрое решение

### Шаг 1: Проверьте наличие библиотек

Откройте терминал в папке проекта и выполните:

```bash
pip list | grep gspread
pip list | grep oauth2client
```

Если не выводятся, установите:

```bash
pip install gspread==5.12.0 oauth2client==4.1.3
```

### Шаг 2: Проверьте credentials.json

Откройте файл и убедитесь, что:
- Он валидный JSON (без синтаксических ошибок)
- Содержит все необходимые поля
- `client_email` имеет формат `*@*.iam.gserviceaccount.com`

### Шаг 3: Включите API в Google Cloud

1. Зайдите в https://console.cloud.google.com/
2. Выберите проект из credentials.json (поле `project_id`)
3. Перейдите в **APIs & Services** → **Library**
4. Найдите и нажмите **ENABLE** для:
   - Google Sheets API
   - Google Drive API

### Шаг 4: Перезапустите бота

```bash
python bot.py
```

При запуске в логах должно появиться:
```
Google Sheets service initialized successfully
```

### Шаг 5: Одобрите пользователя

1. Зайдите в бот
2. `/admin` → **Пользователи** → **На проверке**
3. Выберите пользователя и нажмите **✅ Одобрить**

В логах должно появиться:
```
Registry exported to Google Sheets: https://docs.google.com/spreadsheets/d/SHEET_ID/edit
```

## Где найти созданную таблицу

### Вариант 1: В Google Drive

1. Откройте [Google Drive](https://drive.google.com/)
2. В поиске введите: `owner:YOUR_SERVICE_ACCOUNT_EMAIL`
   - EMAIL можно найти в credentials.json в поле `client_email`
3. Или просто найдите по названию: **"Реестр членов ассоциации КП Лазурный"**

### Вариант 2: В логах бота

После одобрения первого пользователя в логах будет ссылка:
```
Registry exported to Google Sheets: https://docs.google.com/spreadsheets/d/SHEET_ID/edit
```

Скопируйте эту ссылку и откройте в браузере.

### Вариант 3: Поделиться с собой

Если таблица создана Service Account, вы не увидите её в своем Drive автоматически.

**Решение:** В коде бота есть автоматическая публикация таблицы (anyone с правами reader), поэтому по ссылке из логов таблица будет доступна.

Либо можно добавить ваш email в код:

В файле `services/sheets_service.py`, строка 270, добавьте перед `share('', ...)`:

```python
# Share with your email
spreadsheet.share('your-email@gmail.com', perm_type='user', role='writer')

# Make publicly readable
spreadsheet.share('', perm_type='anyone', role='reader')
```

## Частые ошибки

### Ошибка: "gspread not installed"

**Решение:**
```bash
pip install gspread oauth2client
```

### Ошибка: "Failed to initialize Google Sheets client: [Errno 2] No such file or directory: 'credentials.json'"

**Решение:**
- Убедитесь, что credentials.json находится в корне проекта
- Путь: `c:\Users\den\lazurny_bot\credentials.json`

### Ошибка: "Invalid JSON in credentials file"

**Решение:**
- Откройте credentials.json в текстовом редакторе
- Проверьте, что это валидный JSON (можно проверить на jsonlint.com)
- Убедитесь, что файл скачан полностью без обрезок

### Ошибка: "insufficient authentication scopes"

**Решение:**
- Убедитесь, что Google Sheets API и Google Drive API включены в Google Cloud Console
- Пересоздайте Service Account и скачайте новый credentials.json
- Перезапустите бота

### Ошибка: "The caller does not have permission"

**Решение:**
- В Google Cloud Console проверьте, что у Service Account есть права
- Убедитесь, что APIs включены для проекта
- Попробуйте создать новый Service Account с правами **Editor**

## Дополнительная информация

- Подробная инструкция по настройке: [GOOGLE_SHEETS_SETUP.md](GOOGLE_SHEETS_SETUP.md)
- Официальная документация gspread: https://docs.gspread.org/
- Google Cloud Console: https://console.cloud.google.com/

## Поддержка

Если проблема не решается:
1. Проверьте логи бота на наличие ошибок
2. Запустите `test_sheets.py` для диагностики
3. Убедитесь, что все шаги выполнены правильно
