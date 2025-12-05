"""
Configuration module for Lazurny Bot
"""
import os
from dataclasses import dataclass, field
from typing import List
from dotenv import load_dotenv

# Load environment variables
load_dotenv()


@dataclass
class BotConfig:
    """Bot configuration class"""

    # Telegram Bot Settings
    BOT_TOKEN: str = field(default_factory=lambda: os.getenv('BOT_TOKEN', ''))

    # Database Settings
    DATABASE_URL: str = field(default_factory=lambda: os.getenv(
        'DATABASE_URL',
        'sqlite+aiosqlite:///./lazurny_bot.db'
    ))

    # Admin Settings
    ADMIN_IDS: List[int] = field(default_factory=lambda: [
        int(x.strip()) for x in os.getenv('ADMIN_IDS', '').split(',') if x.strip()
    ])

    # Voting Configuration
    VOTE_DURATION_DAYS: int = field(default_factory=lambda: int(os.getenv('VOTE_DURATION_DAYS', '7')))
    DEFAULT_QUORUM_PERCENT: int = field(default_factory=lambda: int(os.getenv('DEFAULT_QUORUM_PERCENT', '50')))

    # Notification Configuration
    REMINDER_HOURS_BEFORE: int = field(default_factory=lambda: int(os.getenv('REMINDER_HOURS_BEFORE', '24')))
    QUIET_HOURS_START: str = field(default_factory=lambda: os.getenv('QUIET_HOURS_START', '22:00'))
    QUIET_HOURS_END: str = field(default_factory=lambda: os.getenv('QUIET_HOURS_END', '08:00'))

    # General Settings
    TIMEZONE: str = field(default_factory=lambda: os.getenv('TIMEZONE', 'Europe/Moscow'))
    DEBUG: bool = field(default_factory=lambda: os.getenv('DEBUG', 'False').lower() == 'true')

    def validate(self):
        """Validate configuration"""
        if not self.BOT_TOKEN:
            raise ValueError("BOT_TOKEN is required")
        if not self.ADMIN_IDS:
            raise ValueError("At least one ADMIN_ID is required")
        return True


# Create global config instance
config = BotConfig()
