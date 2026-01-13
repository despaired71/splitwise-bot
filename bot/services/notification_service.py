"""Service for sending notifications."""

from typing import Dict, List
from decimal import Decimal

from aiogram import Bot
from aiogram.exceptions import TelegramAPIError

from bot.database.models import Event, Participant


class NotificationService:
    """Service for sending notifications to users."""

    def __init__(self, bot: Bot):
        self.bot = bot

    async def notify_calculation_complete(
            self,
            event: Event,
            debts: Dict[int, Dict],
            participants: Dict[int, Participant]
    ):
        """
        Send notifications after debt calculation.

        Args:
            event: Event object
            debts: Result from CalculationService.calculate_debts()
            participants: Dict of participant_id -> Participant
        """
        # Send summary to group chat if exists
        if event.chat_id:
            await self._send_group_summary(event, debts)

        # Send individual notifications to each participant
        for participant_id, debt_info in debts.items():
            participant = participants.get(participant_id)
            if not participant or not participant.user_id:
                continue

            # Only notify if they have debts to pay
            if debt_info["debts"]:
                await self._send_individual_debt_notification(
                    participant.user_id,
                    event,
                    debt_info
                )

    async def _send_group_summary(
            self,
            event: Event,
            debts: Dict[int, Dict]
    ):
        """Send calculation summary to group chat."""
        message = f"💰 <b>Расчет для мероприятия:</b> {event.name}\n\n"
        message += "🧮 <b>Итоги:</b>\n\n"

        # Show who owes whom
        has_debts = False
        for participant_id, debt_info in debts.items():
            if debt_info["debts"]:
                has_debts = True
                message += f"👤 <b>{debt_info['name']}</b> должен:\n"
                for debt in debt_info["debts"]:
                    message += f"  • {debt['to_name']}: {debt['amount']:.2f} ₽\n"
                message += "\n"

        if not has_debts:
            message += "✅ Все расплатились!\n"
        else:
            message += "💡 <i>Каждому отправлено личное сообщение с деталями.</i>"

        try:
            await self.bot.send_message(event.chat_id, message, parse_mode="HTML")
        except TelegramAPIError as e:
            # Log error but don't fail
            print(f"Failed to send group notification: {e}")

    async def _send_individual_debt_notification(
            self,
            user_id: int,
            event: Event,
            debt_info: Dict
    ):
        """Send individual debt notification to user."""
        message = f"💰 <b>Расчет для мероприятия:</b> {event.name}\n\n"

        balance = debt_info["balance"]

        if balance > 0:
            # User is owed money
            message += f"✅ <b>Вам должны: {balance:.2f} ₽</b>\n\n"
            if debt_info["credits"]:
                message += "Получите от:\n"
                for credit in debt_info["credits"]:
                    message += f"  • {credit['from_name']}: {credit['amount']:.2f} ₽\n"

        elif balance < 0:
            # User owes money
            message += f"💸 <b>Вы должны: {abs(balance):.2f} ₽</b>\n\n"
            if debt_info["debts"]:
                message += "Переведите:\n"
                for debt in debt_info["debts"]:
                    message += f"  • {debt['to_name']}: {debt['amount']:.2f} ₽\n"

        else:
            # Balanced
            message += "✅ <b>Вы ни с кем не в долгах!</b>\n"

        try:
            await self.bot.send_message(user_id, message, parse_mode="HTML")
        except TelegramAPIError as e:
            # User might have blocked the bot or not started conversation
            print(f"Failed to send notification to user {user_id}: {e}")

    async def notify_expense_added(
            self,
            event: Event,
            payer_name: str,
            amount: Decimal,
            description: str
    ):
        """Notify group chat about new expense."""
        if not event.chat_id:
            return

        message = (
            f"💰 <b>Новый расход</b>\n\n"
            f"Мероприятие: {event.name}\n"
            f"Кто платил: {payer_name}\n"
            f"Сумма: {amount:.2f} ₽\n"
            f"Описание: {description}"
        )

        try:
            await self.bot.send_message(event.chat_id, message, parse_mode="HTML")
        except TelegramAPIError as e:
            print(f"Failed to send expense notification: {e}")

    async def notify_event_closed(self, event: Event):
        """Notify that event has been closed."""
        if not event.chat_id:
            return

        message = (
            f"🔒 <b>Мероприятие закрыто</b>\n\n"
            f"{event.name}\n\n"
            f"Спасибо за участие! Используйте /calculate для финального расчета."
        )

        try:
            await self.bot.send_message(event.chat_id, message, parse_mode="HTML")
        except TelegramAPIError as e:
            print(f"Failed to send close notification: {e}")