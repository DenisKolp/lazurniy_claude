# Быстрый старт: Настройка OAuth2

## 📝 Краткая инструкция

### Шаг 1: Скачайте OAuth credentials

1. Откройте: https://console.cloud.google.com/apis/credentials
2. Создайте **OAuth 2.0 Client ID** (Desktop app)
3. Скачайте JSON → сохраните как `oauth_credentials.json`
4. Включите **Google Sheets API** и **Google Drive API**

### Шаг 2: Получите токен

```bash
py get_oauth_token.py
```

Откроется браузер → войдите в Google → разрешите доступ → готово!

Будет создан файл `token.json`

### Шаг 3: Запустите бота

```bash
docker-compose build
docker-compose up -d
```

### Шаг 4: Проверьте

```bash
docker logs lazurny_bot --tail 20
```

Должно быть: `Google Sheets service initialized with OAuth2`

### Тестирование

Запустите в контейнере:

```bash
docker exec lazurny_bot python test_sheets_oauth.py
```

Или локально (если есть Python):

```bash
py test_sheets_oauth.py
```

## 🎉 Готово!

Теперь таблицы создаются в вашем Google Drive без проблем с квотой!

---

📖 Подробная инструкция: [GOOGLE_OAUTH_SETUP.md](GOOGLE_OAUTH_SETUP.md)
