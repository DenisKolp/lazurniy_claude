#!/bin/bash

# Update script for Lazurny Bot

set -e

# Colors
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m'

BOT_DIR="/opt/lazurny_bot"

echo -e "${GREEN}Updating Lazurny Bot...${NC}"

# Check if running as root
if [[ $EUID -ne 0 ]]; then
   echo -e "${RED}This script must be run as root${NC}"
   exit 1
fi

cd $BOT_DIR

# Backup database first
echo -e "${YELLOW}Step 1: Creating backup...${NC}"
bash scripts/backup.sh

# Stop the bot
echo -e "${YELLOW}Step 2: Stopping bot...${NC}"
systemctl stop lazurny-bot

# Pull latest changes
echo -e "${YELLOW}Step 3: Pulling latest changes...${NC}"
git fetch origin
git pull origin main

# Update dependencies
echo -e "${YELLOW}Step 4: Updating dependencies...${NC}"
source venv/bin/activate
pip install -r requirements.txt --upgrade

# Start the bot
echo -e "${YELLOW}Step 5: Starting bot...${NC}"
systemctl start lazurny-bot

# Wait a bit and check status
sleep 3
systemctl status lazurny-bot

echo -e "${GREEN}✅ Update complete!${NC}"
echo ""
echo "Monitor logs with: journalctl -u lazurny-bot -f"
