"""Validators for user input."""

import re
from decimal import Decimal, InvalidOperation
from typing import Optional, Tuple


def validate_amount(text: str) -> Tuple[bool, Optional[Decimal], Optional[str]]:
    """
    Validate and parse amount from text.

    Args:
        text: User input text

    Returns:
        Tuple of (is_valid, amount, error_message)
    """
    # Remove spaces and replace comma with dot
    text = text.strip().replace(" ", "").replace(",", ".")

    # Try to parse as decimal
    try:
        amount = Decimal(text)
    except (InvalidOperation, ValueError):
        return False, None, "❌ Некорректный формат суммы. Используйте числа, например: 100 или 150.50"

    # Check if positive
    if amount <= 0:
        return False, None, "❌ Сумма должна быть больше нуля"

    # Check if reasonable (not too large)
    if amount > Decimal("1000000"):
        return False, None, "❌ Сумма слишком большая (максимум 1,000,000)"

    # Round to 2 decimal places
    amount = amount.quantize(Decimal("0.01"))

    return True, amount, None


def validate_event_name(name: str) -> Tuple[bool, Optional[str]]:
    """
    Validate event name.

    Returns:
        Tuple of (is_valid, error_message)
    """
    name = name.strip()

    if not name:
        return False, "❌ Название не может быть пустым"

    if len(name) < 3:
        return False, "❌ Название слишком короткое (минимум 3 символа)"

    if len(name) > 100:
        return False, "❌ Название слишком длинное (максимум 100 символов)"

    return True, None


def validate_participant_name(name: str) -> Tuple[bool, Optional[str]]:
    """
    Validate participant name.

    Returns:
        Tuple of (is_valid, error_message)
    """
    name = name.strip()

    if not name:
        return False, "❌ Имя не может быть пустым"

    if len(name) < 2:
        return False, "❌ Имя слишком короткое (минимум 2 символа)"

    if len(name) > 50:
        return False, "❌ Имя слишком длинное (максимум 50 символов)"

    return True, None


def validate_username(username: str) -> Tuple[bool, Optional[str], Optional[str]]:
    """
    Validate and parse Telegram username.

    Returns:
        Tuple of (is_valid, cleaned_username, error_message)
    """
    username = username.strip()

    if not username:
        return False, None, "❌ Username не может быть пустым"

    # Remove @ if present
    if username.startswith("@"):
        username = username[1:]

    # Check format (alphanumeric + underscore, 5-32 chars)
    if not re.match(r"^[a-zA-Z0-9_]{5,32}$", username):
        return False, None, "❌ Некорректный формат username. Пример: @username"

    return True, username, None


def validate_description(description: str) -> Tuple[bool, Optional[str]]:
    """
    Validate expense description.

    Returns:
        Tuple of (is_valid, error_message)
    """
    description = description.strip()

    if not description:
        return False, "❌ Описание не может быть пустым"

    if len(description) < 3:
        return False, "❌ Описание слишком короткое (минимум 3 символа)"

    if len(description) > 200:
        return False, "❌ Описание слишком длинное (максимум 200 символов)"

    return True, None


def validate_percentage(text: str) -> Tuple[bool, Optional[Decimal], Optional[str]]:
    """
    Validate and parse percentage.

    Returns:
        Tuple of (is_valid, percentage, error_message)
    """
    # Remove spaces and % sign
    text = text.strip().replace(" ", "").replace("%", "").replace(",", ".")

    try:
        percentage = Decimal(text)
    except (InvalidOperation, ValueError):
        return False, None, "❌ Некорректный формат процента"

    if percentage < 0 or percentage > 100:
        return False, None, "❌ Процент должен быть от 0 до 100"

    return True, percentage, None


def parse_user_mention(text: str) -> Optional[int]:
    """
    Parse user ID from mention or text link.

    Args:
        text: Text containing mention (e.g., "tg://user?id=123456")

    Returns:
        User ID or None
    """
    # Try to extract user ID from text link
    match = re.search(r"tg://user\?id=(\d+)", text)
    if match:
        return int(match.group(1))

    return None


def is_valid_split_distribution(
        splits: list,
        total_amount: Decimal,
        split_type: str
) -> Tuple[bool, Optional[str]]:
    """
    Validate that split distribution is correct.

    Args:
        splits: List of split dicts
        total_amount: Total expense amount
        split_type: Type of split (equal, custom, specific)

    Returns:
        Tuple of (is_valid, error_message)
    """
    if not splits:
        return False, "❌ Необходимо указать хотя бы одного участника"

    if split_type == "equal":
        # For equal split, just need participants
        return True, None

    elif split_type == "custom":
        # Check if percentages or amounts sum correctly
        has_percentages = any("share_percentage" in s for s in splits)
        has_amounts = any("share_amount" in s for s in splits)

        if has_percentages:
            total_pct = sum(Decimal(s.get("share_percentage", 0)) for s in splits)
            if abs(total_pct - 100) > Decimal("0.01"):
                return False, f"❌ Сумма процентов должна быть 100% (сейчас {total_pct}%)"

        if has_amounts:
            total = sum(Decimal(s.get("share_amount", 0)) for s in splits)
            if abs(total - total_amount) > Decimal("0.01"):
                return False, f"❌ Сумма долей должна равняться {total_amount} ₽ (сейчас {total} ₽)"

    elif split_type == "specific":
        # Check if specific amounts sum to total
        total = sum(Decimal(s.get("share_amount", 0)) for s in splits)
        if abs(total - total_amount) > Decimal("0.01"):
            return False, f"❌ Сумма должна равняться {total_amount} ₽ (сейчас {total} ₽)"

    return True, None