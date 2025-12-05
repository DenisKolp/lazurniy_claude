#!/bin/bash

# Restore script for Lazurny Bot database

set -e

# Configuration
BACKUP_DIR="/opt/lazurny_bot/backups"
DB_PATH="/opt/lazurny_bot/lazurny_bot.db"

# Colors
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m'

echo -e "${GREEN}Lazurny Bot Database Restore${NC}"
echo ""

# List available backups
echo "Available backups:"
ls -lh $BACKUP_DIR/backup_*.db.gz 2>/dev/null || {
    echo -e "${RED}No backups found!${NC}"
    exit 1
}

echo ""
read -p "Enter backup filename (or full path): " BACKUP_FILE

# Check if file exists
if [ ! -f "$BACKUP_FILE" ] && [ ! -f "$BACKUP_DIR/$BACKUP_FILE" ]; then
    echo -e "${RED}Backup file not found!${NC}"
    exit 1
fi

# Use full path if relative path provided
if [ ! -f "$BACKUP_FILE" ]; then
    BACKUP_FILE="$BACKUP_DIR/$BACKUP_FILE"
fi

echo ""
echo -e "${YELLOW}WARNING: This will replace the current database!${NC}"
read -p "Are you sure? (yes/no): " CONFIRM

if [ "$CONFIRM" != "yes" ]; then
    echo "Restore cancelled."
    exit 0
fi

# Stop the bot
echo -e "${YELLOW}Stopping bot...${NC}"
systemctl stop lazurny-bot

# Backup current database
if [ -f "$DB_PATH" ]; then
    echo "Backing up current database..."
    cp $DB_PATH "${DB_PATH}.before_restore"
fi

# Restore backup
echo "Restoring backup..."
gunzip -c $BACKUP_FILE > $DB_PATH

# Start the bot
echo "Starting bot..."
systemctl start lazurny-bot

# Check status
sleep 2
systemctl status lazurny-bot

echo -e "${GREEN}✅ Restore complete!${NC}"
echo ""
echo "Previous database saved as: ${DB_PATH}.before_restore"
