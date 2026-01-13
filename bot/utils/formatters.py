"""Formatters for displaying data in messages."""

from decimal import Decimal
from typing import Dict, List
from datetime import datetime

from bot.database.models import Event, Participant, Expense, Family


def format_event_info(event: Event) -> str:
    """Format event information for display."""
    status_emoji = {
        "active": "🟢",
        "closed": "🔴",
        "archived": "⚫"
    }

    message = f"<b>📋 Мероприятие:</b> {event.name}\n\n"

    if event.description:
        message += f"<b>Описание:</b> {event.description}\n\n"

    message += f"<b>Статус:</b> {status_emoji.get(event.status, '⚪')} {event.status}\n"
    message += f"<b>Валюта:</b> {event.currency}\n"
    message += f"<b>Создано:</b> {event.created_at.strftime('%d.%m.%Y %H:%M')}\n"

    if event.closed_at:
        message += f"<b>Закрыто:</b> {event.closed_at.strftime('%d.%m.%Y %H:%M')}\n"

    # Statistics
    active_participants = len([p for p in event.participants if p.is_active])
    message += f"\n<b>Участников:</b> {active_participants}\n"
    message += f"<b>Семей:</b> {len(event.families)}\n"

    active_expenses = [e for e in event.expenses if not e.is_deleted]
    total_amount = sum(e.amount for e in active_expenses)
    message += f"<b>Расходов:</b> {len(active_expenses)}\n"
    message += f"<b>Всего потрачено:</b> {total_amount:.2f} ₽\n"

    return message


def format_participants_list(participants: List[Participant]) -> str:
    """Format list of participants."""
    if not participants:
        return "❌ Нет участников"

    message = "<b>👥 Участники:</b>\n\n"

    for i, participant in enumerate(participants, 1):
        icon = "👤" if participant.participant_type == "telegram_chat" else "📝"
        message += f"{i}. {icon} {participant.display_name}"

        if participant.username:
            message += f" (@{participant.username})"

        message += "\n"

    return message


def format_families_list(families: List[Family]) -> str:
    """Format list of families."""
    if not families:
        return "❌ Нет семей"

    message = "<b>👨‍👩‍👧‍👦 Семьи:</b>\n\n"

    for i, family in enumerate(families, 1):
        message += f"{i}. <b>{family.name}</b>\n"

        if family.family_head:
            message += f"   💰 Казначей: {family.family_head.display_name}\n"

        message += f"   Членов: {len(family.members)}\n"

        # List members
        for member in family.members:
            message += f"     • {member.participant.display_name}\n"

        message += "\n"

    return message


def format_expenses_list(expenses: List[Expense]) -> str:
    """Format list of expenses."""
    if not expenses:
        return "❌ Нет расходов"

    message = "<b>💰 Расходы:</b>\n\n"

    for i, expense in enumerate(expenses, 1):
        message += f"{i}. <b>{expense.description}</b>\n"
        message += f"   Сумма: {expense.amount:.2f} ₽\n"
        message += f"   Платил: {expense.payer.display_name}\n"
        message += f"   Дата: {expense.created_at.strftime('%d.%m.%Y %H:%M')}\n"

        if expense.category:
            message += f"   Категория: {expense.category}\n"

        message += "\n"

    return message


def format_expense_detail(expense: Expense) -> str:
    """Format detailed expense information."""
    message = f"<b>💰 Расход #{expense.id}</b>\n\n"
    message += f"<b>Описание:</b> {expense.description}\n"
    message += f"<b>Сумма:</b> {expense.amount:.2f} ₽\n"
    message += f"<b>Платил:</b> {expense.payer.display_name}\n"

    if expense.category:
        message += f"<b>Категория:</b> {expense.category}\n"

    message += f"<b>Дата:</b> {expense.created_at.strftime('%d.%m.%Y %H:%M')}\n"

    # Split information
    split_type_names = {
        "equal": "Поровну",
        "custom": "Свои доли",
        "specific": "Конкретные суммы"
    }
    message += f"<b>Распределение:</b> {split_type_names.get(expense.split_type, expense.split_type)}\n"

    if expense.splits:
        message += "\n<b>Разделено между:</b>\n"
        for split in expense.splits:
            if split.participant_id:
                message += f"  • {split.participant.display_name}"
            elif split.family_id:
                message += f"  • 👨‍👩‍👧‍👦 {split.family.name}"

            if split.share_amount:
                message += f": {split.share_amount:.2f} ₽"
            elif split.share_percentage:
                message += f": {split.share_percentage:.0f}%"

            message += "\n"

    return message


def format_debt_calculation(debts: Dict[int, Dict]) -> str:
    """Format debt calculation results."""
    message = "<b>🧮 Расчет долгов</b>\n\n"

    # Separate into categories
    debtors = []
    creditors = []
    balanced = []

    for participant_id, debt_info in debts.items():
        balance = debt_info["balance"]
        if balance < -0.01:  # Owes money
            debtors.append(debt_info)
        elif balance > 0.01:  # Is owed money
            creditors.append(debt_info)
        else:
            balanced.append(debt_info)

    # Show who owes
    if debtors:
        message += "<b>💸 Должны:</b>\n"
        for debt_info in debtors:
            message += f"\n<b>{debt_info['name']}</b> (всего: {abs(debt_info['balance']):.2f} ₽)\n"
            for debt in debt_info["debts"]:
                message += f"  → {debt['to_name']}: {debt['amount']:.2f} ₽\n"
        message += "\n"

    # Show who is owed
    if creditors:
        message += "<b>✅ Им должны:</b>\n"
        for debt_info in creditors:
            message += f"\n<b>{debt_info['name']}</b> (всего: {debt_info['balance']:.2f} ₽)\n"
            for credit in debt_info["credits"]:
                message += f"  ← {credit['from_name']}: {credit['amount']:.2f} ₽\n"
        message += "\n"

    # Show balanced
    if balanced:
        message += "<b>⚖️ Расплатились:</b>\n"
        for debt_info in balanced:
            message += f"  • {debt_info['name']}\n"

    return message


def format_expense_summary(summary: Dict) -> str:
    """Format expense summary statistics."""
    message = "<b>📊 Статистика расходов</b>\n\n"
    message += f"<b>Всего потрачено:</b> {summary['total_amount']:.2f} ₽\n"
    message += f"<b>Количество расходов:</b> {summary['expense_count']}\n\n"

    if summary['by_category']:
        message += "<b>По категориям:</b>\n"
        for category, amount in sorted(
                summary['by_category'].items(),
                key=lambda x: x[1],
                reverse=True
        ):
            percentage = (amount / summary['total_amount'] * 100) if summary['total_amount'] > 0 else 0
            message += f"  • {category}: {amount:.2f} ₽ ({percentage:.1f}%)\n"
        message += "\n"

    if summary['by_participant']:
        message += "<b>Кто сколько платил:</b>\n"
        for participant, amount in sorted(
                summary['by_participant'].items(),
                key=lambda x: x[1],
                reverse=True
        ):
            percentage = (amount / summary['total_amount'] * 100) if summary['total_amount'] > 0 else 0
            message += f"  • {participant}: {amount:.2f} ₽ ({percentage:.1f}%)\n"

    return message


def format_amount(amount: Decimal) -> str:
    """Format amount with currency."""
    return f"{amount:.2f} ₽"


def format_date(dt: datetime) -> str:
    """Format datetime for display."""
    return dt.strftime("%d.%m.%Y %H:%M")


def truncate_text(text: str, max_length: int = 50) -> str:
    """Truncate text to max length."""
    if len(text) <= max_length:
        return text
    return text[:max_length - 3] + "..."