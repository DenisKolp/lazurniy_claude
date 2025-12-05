"""
Validation functions
"""
import re
from typing import Optional
import phonenumbers


def validate_phone_number(phone: str) -> Optional[str]:
    """
    Validate and format phone number
    Returns formatted number or None if invalid
    """
    # Remove all non-digit characters except +
    cleaned = re.sub(r'[^\d+]', '', phone)

    # If starts with 8, replace with +7
    if cleaned.startswith('8') and len(cleaned) == 11:
        cleaned = '+7' + cleaned[1:]
    # If starts with 7 (without +), add +
    elif cleaned.startswith('7') and len(cleaned) == 11:
        cleaned = '+' + cleaned
    # If 10 digits, add +7
    elif cleaned.isdigit() and len(cleaned) == 10:
        cleaned = '+7' + cleaned

    try:
        parsed = phonenumbers.parse(cleaned, "RU")
        if phonenumbers.is_valid_number(parsed):
            return phonenumbers.format_number(
                parsed,
                phonenumbers.PhoneNumberFormat.E164
            )
    except phonenumbers.NumberParseException:
        pass
    return None


def validate_document(file_name: str) -> bool:
    """Validate document file extension"""
    allowed_extensions = ['.pdf', '.jpg', '.jpeg', '.png', '.doc', '.docx']
    return any(file_name.lower().endswith(ext) for ext in allowed_extensions)


def validate_title(title: str, min_length: int = 5, max_length: int = 500) -> bool:
    """Validate title length"""
    return min_length <= len(title.strip()) <= max_length


def validate_description(description: str, min_length: int = 10, max_length: int = 4000) -> bool:
    """Validate description length"""
    return min_length <= len(description.strip()) <= max_length


def validate_voting_options(options: list) -> bool:
    """Validate voting options"""
    if not isinstance(options, list):
        return False
    if len(options) < 2:
        return False
    if len(options) > 10:
        return False
    return all(isinstance(opt, str) and len(opt.strip()) > 0 for opt in options)


def validate_address(address: str) -> Optional[str]:
    """
    Validate address format for KP Lazurny
    Accepts: house number (e.g., "173", "173/1") or street + house number (e.g., "Лазурная 173", "Лазурная 173/1")
    Returns normalized address or None if invalid
    """
    address = address.strip()

    # Pattern 1: Just house number (with optional fraction): 173, 173/1
    pattern_house_only = r'^(\d+(?:/\d+)?)$'

    # Pattern 2: Street name + house number: Лазурная 173, Лазурная 173/1
    pattern_with_street = r'^([а-яА-ЯёЁ]+)\s+(\d+(?:/\d+)?)$'

    match = re.match(pattern_house_only, address)
    if match:
        return match.group(1)

    match = re.match(pattern_with_street, address)
    if match:
        street = match.group(1).capitalize()
        house = match.group(2)
        return f"{street} {house}"

    return None
