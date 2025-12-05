#!/bin/bash

# Backup script for Lazurny Bot database

set -e

# Configuration
BACKUP_DIR="/opt/lazurny_bot/backups"
DB_PATH="/opt/lazurny_bot/lazurny_bot.db"
TIMESTAMP=$(date +"%Y%m%d_%H%M%S")
BACKUP_FILE="$BACKUP_DIR/backup_$TIMESTAMP.db"
DAYS_TO_KEEP=7

# Colors
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

echo -e "${GREEN}Starting backup...${NC}"

# Create backup directory if it doesn't exist
mkdir -p $BACKUP_DIR

# Check if database exists
if [ ! -f "$DB_PATH" ]; then
    echo "Error: Database file not found at $DB_PATH"
    exit 1
fi

# Create backup
echo "Creating backup: $BACKUP_FILE"
cp $DB_PATH $BACKUP_FILE

# Compress backup
echo "Compressing backup..."
gzip $BACKUP_FILE

# Remove old backups
echo "Removing backups older than $DAYS_TO_KEEP days..."
find $BACKUP_DIR -name "backup_*.db.gz" -mtime +$DAYS_TO_KEEP -delete

# Show backup info
BACKUP_SIZE=$(du -h "$BACKUP_FILE.gz" | cut -f1)
echo -e "${GREEN}Backup completed successfully!${NC}"
echo "File: $BACKUP_FILE.gz"
echo "Size: $BACKUP_SIZE"

# List recent backups
echo ""
echo "Recent backups:"
ls -lh $BACKUP_DIR/backup_*.db.gz | tail -5
