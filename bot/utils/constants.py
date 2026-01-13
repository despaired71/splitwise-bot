"""Constants used throughout the bot."""

from enum import Enum


class EventStatus(str, Enum):
    """Event status types."""
    ACTIVE = "active"
    CLOSED = "closed"
    ARCHIVED = "archived"


class ParticipantType(str, Enum):
    """Participant types."""
    TELEGRAM_CHAT = "telegram_chat"      # User in the chat
    TELEGRAM_EXTERNAL = "telegram_external"  # Telegram user not in chat
    EXTERNAL = "external"                 # Non-Telegram user


class SplitType(str, Enum):
    """How expense is split."""
    EQUAL = "equal"        # Split equally among all
    CUSTOM = "custom"      # Custom amounts/percentages
    SPECIFIC = "specific"  # Specific people/families


class AuditAction(str, Enum):
    """Audit log actions."""
    CREATE = "create"
    UPDATE = "update"
    DELETE = "delete"


# Bot commands
CMD_START = "start"
CMD_HELP = "help"
CMD_NEW_EVENT = "new_event"
CMD_LIST_EVENTS = "list_events"
CMD_EVENT_INFO = "event_info"
CMD_EDIT_EVENT = "edit_event"
CMD_DELETE_EVENT = "delete_event"
CMD_CLOSE_EVENT = "close_event"

CMD_JOIN_EVENT = "join_event"
CMD_ADD_PARTICIPANT = "add_participant"
CMD_REMOVE_PARTICIPANT = "remove_participant"
CMD_LIST_PARTICIPANTS = "list_participants"

CMD_CREATE_FAMILY = "create_family"
CMD_ADD_TO_FAMILY = "add_to_family"
CMD_REMOVE_FROM_FAMILY = "remove_from_family"
CMD_LIST_FAMILIES = "list_families"

CMD_MY_FAMILIES = "my_families"
CMD_CREATE_FAMILY_TEMPLATE = "create_family_template"
CMD_EDIT_FAMILY_TEMPLATE = "edit_family_template"
CMD_DELETE_FAMILY_TEMPLATE = "delete_family_template"

CMD_ADD_EXPENSE = "add_expense"
CMD_EDIT_EXPENSE = "edit_expense"
CMD_DELETE_EXPENSE = "delete_expense"
CMD_MY_EXPENSES = "my_expenses"
CMD_ALL_EXPENSES = "all_expenses"

CMD_CALCULATE = "calculate"
CMD_MY_DEBTS = "my_debts"

# Callback data prefixes
CB_EVENT = "event"
CB_PARTICIPANT = "participant"
CB_FAMILY = "family"
CB_EXPENSE = "expense"
CB_CALCULATE = "calc"
CB_CONFIRM = "confirm"
CB_CANCEL = "cancel"

# Messages
MSG_WELCOME = """
👋 Привет! Я бот для учета расходов в компании.

Я помогу:
• Создавать мероприятия и добавлять участников
• Учитывать расходы каждого
• Объединять людей в семьи
• Рассчитывать, кто кому сколько должен

Используй /help для списка команд.
"""

MSG_HELP = """
📖 <b>Доступные команды:</b>

<b>Мероприятия:</b>
/new_event - создать новое мероприятие
/list_events - список мероприятий
/event_info - информация о мероприятии
/close_event - закрыть мероприятие

<b>Участники:</b>
/join_event - присоединиться к мероприятию
/add_participant - добавить участника
/list_participants - список участников

<b>Семьи:</b>
/create_family - создать семью
/my_families - мои шаблоны семей
/list_families - семьи в мероприятии

<b>Расходы:</b>
/add_expense - добавить расход
/my_expenses - мои расходы
/all_expenses - все расходы (для создателя)

<b>Расчеты:</b>
/calculate - рассчитать долги
/my_debts - мои долги
"""

# Error messages
ERR_NO_EVENT = "❌ Мероприятие не найдено"
ERR_NO_PERMISSION = "❌ У вас нет прав для этого действия"
ERR_INVALID_AMOUNT = "❌ Некорректная сумма"
ERR_PARTICIPANT_HAS_EXPENSES = "❌ У участника есть расходы. Сначала удалите их."
ERR_DATABASE = "❌ Ошибка базы данных"