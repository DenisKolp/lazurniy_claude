# Настройка OAuth2 для Google Sheets

Эта инструкция поможет настроить аутентификацию через OAuth2, чтобы бот мог создавать таблицы в вашем личном Google Drive без проблем с квотой.

## Шаг 1: Создание OAuth 2.0 Client ID

1. Откройте [Google Cloud Console](https://console.cloud.google.com/)

2. Выберите ваш проект (или создайте новый)

3. Перейдите в **APIs & Services** → **Credentials**
   - URL: https://console.cloud.google.com/apis/credentials

4. Нажмите **+ CREATE CREDENTIALS** → **OAuth client ID**

5. Если потребуется, настройте OAuth consent screen:
   - User Type: **External**
   - App name: **Lazurny Bot**
   - User support email: ваш email
   - Developer contact: ваш email
   - Scopes: можно пропустить (настроим позже)
   - Test users: добавьте свой Google аккаунт

6. Вернитесь к созданию OAuth client ID:
   - Application type: **Desktop app**
   - Name: **Lazurny Bot Desktop**

7. Нажмите **CREATE**

8. Скачайте JSON файл с credentials:
   - Нажмите на иконку скачивания
   - Сохраните файл как `oauth_credentials.json` в корне проекта

## Шаг 2: Включение необходимых API

1. Перейдите в **APIs & Services** → **Enabled APIs & services**

2. Нажмите **+ ENABLE APIS AND SERVICES**

3. Найдите и включите следующие API:
   - **Google Sheets API**
   - **Google Drive API**

## Шаг 3: Получение OAuth токена

Теперь нужно запустить скрипт для получения токена.

### На Windows:

```bash
# Установите зависимости (если ещё не установлены)
pip install google-auth google-auth-oauthlib google-auth-httplib2 gspread

# Запустите скрипт
python get_oauth_token.py
```

### На Linux/Mac:

```bash
# Установите зависимости
pip3 install google-auth google-auth-oauthlib google-auth-httplib2 gspread

# Запустите скрипт
python3 get_oauth_token.py
```

### Что произойдет:

1. Откроется браузер с запросом на авторизацию
2. Войдите в ваш Google аккаунт
3. Разрешите доступ к Google Sheets и Google Drive
4. Скрипт сохранит токен в файл `token.json`

**Важно**: Файл `token.json` содержит чувствительные данные. Не делитесь им и не загружайте в публичные репозитории!

## Шаг 4: Добавление token.json в Docker

Обновите `docker-compose.yml`, чтобы пробросить файл с токеном в контейнер:

```yaml
services:
  bot:
    volumes:
      - ./token.json:/app/token.json:ro
```

Или скопируйте файл напрямую:

```bash
# Остановите контейнер
docker-compose down

# Скопируйте token.json в контейнер при следующем запуске
# (файл уже примонтирован через docker-compose.yml)

# Пересоберите и запустите
docker-compose build
docker-compose up -d
```

## Шаг 5: Проверка работы

После запуска бота, проверьте логи:

```bash
docker logs lazurny_bot --tail 50
```

Вы должны увидеть:
```
Google Sheets service initialized with OAuth2 (folder_id: 1iewKOoT5q7Cy5YQxg6BfuR0pA9U3StaE)
```

## Тестирование

Теперь можно протестировать создание таблицы:

```bash
docker exec lazurny_bot python test_sheets.py
```

Таблица должна успешно создаться в вашем Google Drive в указанной папке!

## Обновление токена

OAuth токены периодически истекают. Для обновления токена:

1. Удалите старый `token.json`
2. Запустите снова `python get_oauth_token.py`
3. Скопируйте новый токен в Docker контейнер
4. Перезапустите бот: `docker-compose restart`

## Troubleshooting

### Ошибка: "oauth_credentials.json not found"
- Убедитесь, что вы скачали credentials из Google Cloud Console
- Файл должен называться именно `oauth_credentials.json`

### Ошибка: "Access blocked: This app's request is invalid"
- Убедитесь, что вы добавили свой email в Test users в OAuth consent screen
- Проверьте, что включены Google Sheets API и Google Drive API

### Ошибка: "Token has been expired or revoked"
- Удалите `token.json` и создайте новый токен
- Запустите `python get_oauth_token.py` снова

## Файлы

После настройки у вас должны быть следующие файлы:

- `oauth_credentials.json` - OAuth 2.0 Client credentials (не загружайте в git!)
- `token.json` - OAuth токен пользователя (не загружайте в git!)
- `credentials.json` - Service Account credentials (оставьте как fallback)

Добавьте в `.gitignore`:
```
oauth_credentials.json
token.json
```
