"""
Helper functions
"""
from datetime import datetime, time
from typing import Optional
import pytz
from config import config


def format_datetime(dt: datetime, format_str: str = "%d.%m.%Y %H:%M") -> str:
    """Format datetime to string with timezone"""
    tz = pytz.timezone(config.TIMEZONE)
    local_dt = dt.replace(tzinfo=pytz.UTC).astimezone(tz)
    return local_dt.strftime(format_str)


def is_quiet_hours() -> bool:
    """Check if current time is in quiet hours"""
    tz = pytz.timezone(config.TIMEZONE)
    now = datetime.now(tz).time()

    start_time = time(*map(int, config.QUIET_HOURS_START.split(':')))
    end_time = time(*map(int, config.QUIET_HOURS_END.split(':')))

    if start_time < end_time:
        return start_time <= now <= end_time
    else:
        return now >= start_time or now <= end_time


def escape_markdown(text: str) -> str:
    """Escape special characters for Telegram MarkdownV2"""
    special_chars = ['_', '*', '[', ']', '(', ')', '~', '`', '>', '#', '+', '-', '=', '|', '{', '}', '.', '!']
    for char in special_chars:
        text = text.replace(char, f'\\{char}')
    return text


def truncate_text(text: str, max_length: int = 100) -> str:
    """Truncate text with ellipsis"""
    if len(text) <= max_length:
        return text
    return text[:max_length - 3] + "..."


def get_user_display_name(user) -> str:
    """Get user display name"""
    if user.first_name and user.last_name:
        return f"{user.first_name} {user.last_name}"
    elif user.first_name:
        return user.first_name
    elif user.username:
        return f"@{user.username}"
    else:
        return f"User {user.telegram_id}"


def calculate_quorum(total_users: int, quorum_percent: int) -> int:
    """Calculate required number of votes for quorum"""
    return int((total_users * quorum_percent) / 100)


def format_voting_results(voting, results: dict) -> str:
    """Format voting results as text"""
    import json
    options = json.loads(voting.options) if isinstance(voting.options, str) else voting.options

    text = f"📊 *Результаты голосования*\n\n"
    text += f"*{voting.title}*\n\n"

    total = sum(results.values())
    for i, option in enumerate(options):
        votes = results.get(i, 0)
        percent = (votes / total * 100) if total > 0 else 0
        text += f"{i+1}. {option}: {votes} ({percent:.1f}%)\n"

    text += f"\nВсего голосов: {total}"
    return text
