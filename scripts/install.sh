#!/bin/bash

# Installation script for Lazurny Bot on Ubuntu/Debian

set -e

echo "🚀 Installing Lazurny Bot..."

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Check if running as root
if [[ $EUID -ne 0 ]]; then
   echo -e "${RED}This script must be run as root${NC}"
   exit 1
fi

echo -e "${GREEN}Step 1: Updating system...${NC}"
apt update && apt upgrade -y

echo -e "${GREEN}Step 2: Installing dependencies...${NC}"
apt install -y python3.11 python3-pip python3-venv git

echo -e "${GREEN}Step 3: Creating directory...${NC}"
mkdir -p /opt/lazurny_bot
cd /opt/lazurny_bot

echo -e "${GREEN}Step 4: Cloning repository...${NC}"
read -p "Enter repository URL: " REPO_URL
git clone $REPO_URL .

echo -e "${GREEN}Step 5: Creating virtual environment...${NC}"
python3 -m venv venv
source venv/bin/activate

echo -e "${GREEN}Step 6: Installing Python packages...${NC}"
pip install -r requirements.txt

echo -e "${GREEN}Step 7: Setting up environment file...${NC}"
if [ ! -f .env ]; then
    cp .env.example .env
    echo -e "${YELLOW}Please edit .env file with your configuration:${NC}"
    echo "nano .env"
    read -p "Press enter when ready to continue..."
fi

echo -e "${GREEN}Step 8: Creating systemd service...${NC}"
cat > /etc/systemd/system/lazurny-bot.service << EOF
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

[Install]
WantedBy=multi-user.target
EOF

echo -e "${GREEN}Step 9: Starting service...${NC}"
systemctl daemon-reload
systemctl enable lazurny-bot
systemctl start lazurny-bot

echo -e "${GREEN}Step 10: Checking status...${NC}"
systemctl status lazurny-bot

echo -e "${GREEN}✅ Installation complete!${NC}"
echo ""
echo "Useful commands:"
echo "  - Check status: systemctl status lazurny-bot"
echo "  - View logs: journalctl -u lazurny-bot -f"
echo "  - Restart: systemctl restart lazurny-bot"
echo "  - Stop: systemctl stop lazurny-bot"
