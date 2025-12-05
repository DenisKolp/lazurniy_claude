# 🚀 Руководство по развертыванию

Подробные инструкции по развертыванию Lazurny Bot на различных платформах.

## Содержание

1. [Локальная разработка](#локальная-разработка)
2. [Ubuntu/Debian VPS](#ubuntudebian-vps)
3. [CentOS/RHEL VPS](#centosrhel-vps)
4. [Docker](#docker)
5. [Railway](#railway)
6. [Heroku](#heroku)
7. [DigitalOcean](#digitalocean)
8. [AWS EC2](#aws-ec2)

---

## Локальная разработка

### Windows

```powershell
# 1. Установите Python 3.11+
# Скачайте с python.org

# 2. Клонируйте проект
git clone <repo-url>
cd lazurny_bot

# 3. Создайте виртуальное окружение
python -m venv venv
venv\Scripts\activate

# 4. Установите зависимости
pip install -r requirements.txt

# 5. Настройте .env
copy .env.example .env
notepad .env

# 6. Запустите бота
python bot.py
```

### Linux/macOS

```bash
# 1. Установите Python 3.11+
sudo apt install python3.11 python3-pip  # Ubuntu/Debian
brew install python@3.11                  # macOS

# 2. Клонируйте проект
git clone <repo-url>
cd lazurny_bot

# 3. Создайте виртуальное окружение
python3 -m venv venv
source venv/bin/activate

# 4. Установите зависимости
pip install -r requirements.txt

# 5. Настройте .env
cp .env.example .env
nano .env

# 6. Запустите бота
python bot.py
```

---

## Ubuntu/Debian VPS

### Автоматическая установка

```bash
# Скачайте и запустите скрипт установки
wget https://raw.githubusercontent.com/your-repo/lazurny_bot/main/scripts/install.sh
chmod +x install.sh
sudo ./install.sh
```

### Ручная установка

#### 1. Подготовка сервера

```bash
# Подключитесь к серверу
ssh root@your-server-ip

# Обновите систему
apt update && apt upgrade -y

# Установите зависимости
apt install -y python3.11 python3-pip python3-venv git wget curl
```

#### 2. Установка бота

```bash
# Создайте директорию
mkdir -p /opt/lazurny_bot
cd /opt/lazurny_bot

# Клонируйте репозиторий
git clone <repo-url> .

# Создайте виртуальное окружение
python3 -m venv venv
source venv/bin/activate

# Установите зависимости
pip install -r requirements.txt
```

#### 3. Конфигурация

```bash
# Создайте .env
cp .env.example .env
nano .env
```

Заполните:
```env
BOT_TOKEN=your_token
ADMIN_IDS=123456789
DATABASE_URL=sqlite+aiosqlite:///./data/lazurny_bot.db
```

#### 4. Создайте директории

```bash
mkdir -p data logs backups
chmod 755 data logs backups
```

#### 5. Настройте systemd service

```bash
nano /etc/systemd/system/lazurny-bot.service
```

Содержимое:
```ini
[Unit]
Description=Lazurny Telegram Bot
After=network.target

[Service]
Type=simple
User=root
WorkingDirectory=/opt/lazurny_bot
Environment="PATH=/opt/lazurny_bot/venv/bin"
ExecStart=/opt/lazurny_bot/venv/bin/python /opt/lazurny_bot/bot.py
Restart=always
RestartSec=10
StandardOutput=append:/opt/lazurny_bot/logs/bot.log
StandardError=append:/opt/lazurny_bot/logs/error.log

[Install]
WantedBy=multi-user.target
```

#### 6. Запустите сервис

```bash
systemctl daemon-reload
systemctl enable lazurny-bot
systemctl start lazurny-bot
systemctl status lazurny-bot
```

#### 7. Настройте автоматический backup

```bash
# Сделайте скрипт исполняемым
chmod +x scripts/backup.sh

# Добавьте в crontab
crontab -e
```

Добавьте строку (ежедневный backup в 3:00):
```
0 3 * * * /opt/lazurny_bot/scripts/backup.sh
```

#### 8. Настройте firewall (опционально)

```bash
# Разрешите SSH и HTTPS
ufw allow ssh
ufw allow https
ufw enable
```

---

## CentOS/RHEL VPS

```bash
# 1. Обновите систему
sudo yum update -y

# 2. Установите Python 3.11
sudo yum install -y python3.11 python3-pip git

# 3. Следуйте шагам из раздела Ubuntu/Debian
# начиная с "Установка бота"

# 4. Для systemd используйте те же команды
```

---

## Docker

### Использование Docker Compose (рекомендуется)

#### 1. Установите Docker и Docker Compose

```bash
# Ubuntu/Debian
curl -fsSL https://get.docker.com -o get-docker.sh
sudo sh get-docker.sh
sudo apt install docker-compose -y

# Проверьте установку
docker --version
docker-compose --version
```

#### 2. Подготовьте проект

```bash
git clone <repo-url>
cd lazurny_bot

# Создайте .env
cp .env.example .env
nano .env
```

#### 3. Запустите

```bash
# Сборка и запуск
docker-compose up -d

# Просмотр логов
docker-compose logs -f bot

# Остановка
docker-compose down

# Перезапуск
docker-compose restart bot
```

### Использование только Docker

```bash
# Сборка образа
docker build -t lazurny-bot .

# Запуск контейнера
docker run -d \
  --name lazurny-bot \
  --env-file .env \
  -v $(pwd)/data:/app/data \
  -v $(pwd)/logs:/app/logs \
  --restart unless-stopped \
  lazurny-bot

# Просмотр логов
docker logs -f lazurny-bot

# Остановка
docker stop lazurny-bot

# Удаление
docker rm lazurny-bot
```

### С PostgreSQL

Раскомментируйте секцию PostgreSQL в `docker-compose.yml`:

```yaml
postgres:
  image: postgres:15-alpine
  environment:
    POSTGRES_DB: lazurny_bot
    POSTGRES_USER: lazurny_user
    POSTGRES_PASSWORD: ${POSTGRES_PASSWORD}
  volumes:
    - postgres_data:/var/lib/postgresql/data
```

Обновите `.env`:
```env
DATABASE_URL=postgresql+asyncpg://lazurny_user:password@postgres:5432/lazurny_bot
POSTGRES_PASSWORD=your_secure_password
```

---

## Railway

### 1. Подготовка

1. Создайте аккаунт на [Railway.app](https://railway.app)
2. Подключите GitHub аккаунт
3. Загрузите код в GitHub репозиторий

### 2. Создание проекта

1. Войдите в Railway Dashboard
2. Нажмите "New Project"
3. Выберите "Deploy from GitHub repo"
4. Выберите ваш репозиторий

### 3. Настройка переменных окружения

В разделе "Variables" добавьте:

```
BOT_TOKEN=your_bot_token
ADMIN_IDS=123456789
DATABASE_URL=sqlite+aiosqlite:///./data/lazurny_bot.db
TIMEZONE=Europe/Moscow
DEBUG=False
VOTE_DURATION_DAYS=7
DEFAULT_QUORUM_PERCENT=50
REMINDER_HOURS_BEFORE=24
QUIET_HOURS_START=22:00
QUIET_HOURS_END=08:00
```

### 4. Добавьте PostgreSQL (рекомендуется)

1. Нажмите "New" → "Database" → "PostgreSQL"
2. Railway автоматически создаст переменную `DATABASE_URL`
3. Измените её на формат asyncpg:
```
postgresql+asyncpg://user:password@host:port/database
```

### 5. Deploy

- Railway автоматически развернет бота
- При каждом push в GitHub будет автоматический deploy
- Логи доступны в разделе "Deployments"

### 6. Мониторинг

- Просматривайте логи в реальном времени
- Метрики использования ресурсов
- История deployments

---

## Heroku

### 1. Подготовка

```bash
# Установите Heroku CLI
curl https://cli-assets.heroku.com/install.sh | sh

# Войдите в аккаунт
heroku login
```

### 2. Создание приложения

```bash
cd lazurny_bot

# Создайте приложение
heroku create lazurny-bot

# Добавьте PostgreSQL
heroku addons:create heroku-postgresql:mini

# Настройте переменные
heroku config:set BOT_TOKEN=your_token
heroku config:set ADMIN_IDS=123456789
heroku config:set TIMEZONE=Europe/Moscow

# Получите DATABASE_URL
heroku config:get DATABASE_URL
```

### 3. Измените DATABASE_URL

```bash
# Heroku использует postgres://, нужно изменить на postgresql+asyncpg://
# В настройках Dashboard измените DATABASE_URL
```

### 4. Deploy

```bash
# Инициализируйте git (если не сделано)
git init
git add .
git commit -m "Initial commit"

# Deploy
git push heroku main

# Просмотр логов
heroku logs --tail

# Проверка статуса
heroku ps
```

### 5. Масштабирование

```bash
# Запустите worker
heroku ps:scale worker=1

# Остановите
heroku ps:scale worker=0
```

---

## DigitalOcean

### 1. Создание Droplet

1. Войдите в DigitalOcean
2. Create → Droplets
3. Выберите:
   - Ubuntu 22.04 LTS
   - Basic plan ($6/month)
   - Регион ближайший к пользователям
4. Добавьте SSH ключ
5. Create Droplet

### 2. Подключение

```bash
ssh root@your-droplet-ip
```

### 3. Установка

Следуйте инструкциям из раздела [Ubuntu/Debian VPS](#ubuntudebian-vps)

### 4. Настройка Managed Database (опционально)

1. Create → Databases → PostgreSQL
2. Скопируйте connection string
3. Измените формат на `postgresql+asyncpg://...`
4. Добавьте в `.env`

### 5. Настройка резервного копирования

```bash
# Включите автоматические snapshots
# В настройках Droplet → Backups
```

---

## AWS EC2

### 1. Создание EC2 Instance

1. Войдите в AWS Console
2. EC2 → Launch Instance
3. Выберите:
   - Ubuntu Server 22.04 LTS
   - t2.micro (free tier)
   - Security Group: SSH (22), HTTPS (443)
4. Create key pair
5. Launch

### 2. Подключение

```bash
chmod 400 your-key.pem
ssh -i your-key.pem ubuntu@ec2-ip-address
```

### 3. Установка

```bash
# Переключитесь на root
sudo su -

# Следуйте инструкциям из Ubuntu/Debian VPS
```

### 4. Настройка RDS (опционально)

1. RDS → Create database → PostgreSQL
2. Выберите Free tier
3. Скопируйте endpoint
4. Настройте Security Group для доступа
5. Используйте в DATABASE_URL

### 5. Elastic IP (рекомендуется)

1. EC2 → Elastic IPs → Allocate
2. Associate с вашим instance
3. Используйте статический IP

---

## Общие рекомендации

### Безопасность

1. **Используйте SSH ключи** вместо паролей
2. **Настройте firewall** (ufw, iptables)
3. **Регулярно обновляйте** систему
4. **Используйте fail2ban** для защиты от brute-force
5. **Храните секреты в .env**, не в коде

### Мониторинг

1. **Настройте логирование**
2. **Мониторьте использование ресурсов**
3. **Настройте алерты** при сбоях
4. **Проверяйте логи регулярно**

### Backup

1. **Автоматический backup БД** (ежедневно)
2. **Хранение backups** минимум 7 дней
3. **Тестирование восстановления** регулярно
4. **Backup кода** в Git

### Performance

1. **Используйте PostgreSQL** для продакшена
2. **Настройте индексы** в БД
3. **Мониторьте время отклика**
4. **Оптимизируйте запросы** при необходимости

---

## Troubleshooting

### Бот не запускается

```bash
# Проверьте логи
journalctl -u lazurny-bot -n 50
docker-compose logs bot

# Проверьте конфигурацию
cat .env

# Проверьте права
ls -la /opt/lazurny_bot
```

### База данных не работает

```bash
# SQLite
ls -la lazurny_bot.db
sqlite3 lazurny_bot.db ".tables"

# PostgreSQL
psql $DATABASE_URL -c "\dt"
```

### Высокое использование памяти

```bash
# Перезапустите бота
systemctl restart lazurny-bot

# Проверьте логи на утечки памяти
```

---

## Контакты и поддержка

При проблемах с развертыванием:
1. Проверьте [README.md](README.md)
2. Изучите логи
3. Создайте issue на GitHub

---

**Успешного развертывания!** 🚀
