"""Service for managing expenses."""

from datetime import datetime
from decimal import Decimal
from typing import List, Optional, Dict

from sqlalchemy import select, and_
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from bot.database.models import Expense, ExpenseSplit, Participant, AuditLog
from bot.utils.constants import SplitType, AuditAction


class ExpenseService:
    """Service for expense operations."""

    def __init__(self, session: AsyncSession):
        self.session = session

    async def create_expense(
            self,
            event_id: int,
            payer_id: int,
            amount: Decimal,
            description: str,
            split_type: SplitType,
            splits: List[Dict],
            category: Optional[str] = None
    ) -> Expense:
        """
        Create a new expense.

        Args:
            event_id: Event ID
            payer_id: Participant ID who paid
            amount: Amount paid
            description: Expense description
            split_type: How to split (equal, custom, specific)
            splits: List of split dicts with keys:
                - participant_id or family_id
                - share_amount (optional, for custom/specific)
                - share_percentage (optional, for custom)
            category: Optional category

        Returns:
            Created expense
        """
        expense = Expense(
            event_id=event_id,
            payer_id=payer_id,
            amount=amount,
            description=description,
            split_type=split_type,
            category=category
        )

        self.session.add(expense)
        await self.session.flush()

        # Create splits
        for split_data in splits:
            split = ExpenseSplit(
                expense_id=expense.id,
                participant_id=split_data.get("participant_id"),
                family_id=split_data.get("family_id"),
                share_amount=split_data.get("share_amount"),
                share_percentage=split_data.get("share_percentage")
            )
            self.session.add(split)

        # Log creation
        await self._log_action(
            event_id=event_id,
            user_id=payer_id,
            entity_type="expense",
            entity_id=expense.id,
            action=AuditAction.CREATE,
            new_data={
                "amount": float(amount),
                "description": description,
                "split_type": split_type
            }
        )

        return expense

    async def get_expense(self, expense_id: int) -> Optional[Expense]:
        """Get expense by ID with splits loaded."""
        result = await self.session.execute(
            select(Expense)
            .where(and_(
                Expense.id == expense_id,
                Expense.is_deleted == False
            ))
            .options(
                selectinload(Expense.splits),
                selectinload(Expense.payer)
            )
        )
        return result.scalar_one_or_none()

    async def get_event_expenses(
            self,
            event_id: int,
            include_deleted: bool = False
    ) -> List[Expense]:
        """Get all expenses for an event."""
        query = select(Expense).where(Expense.event_id == event_id)

        if not include_deleted:
            query = query.where(Expense.is_deleted == False)

        query = query.order_by(Expense.created_at.desc())
        query = query.options(selectinload(Expense.payer))

        result = await self.session.execute(query)
        return list(result.scalars().all())

    async def get_participant_expenses(
            self,
            participant_id: int
    ) -> List[Expense]:
        """Get all expenses paid by a participant."""
        result = await self.session.execute(
            select(Expense)
            .where(and_(
                Expense.payer_id == participant_id,
                Expense.is_deleted == False
            ))
            .order_by(Expense.created_at.desc())
        )
        return list(result.scalars().all())

    async def update_expense(
            self,
            expense_id: int,
            user_id: int,
            amount: Optional[Decimal] = None,
            description: Optional[str] = None,
            category: Optional[str] = None
    ) -> Optional[Expense]:
        """Update expense details."""
        expense = await self.get_expense(expense_id)
        if not expense:
            return None

        old_data = {
            "amount": float(expense.amount),
            "description": expense.description,
            "category": expense.category
        }
        new_data = {}

        if amount is not None:
            expense.amount = amount
            new_data["amount"] = float(amount)

        if description is not None:
            expense.description = description
            new_data["description"] = description

        if category is not None:
            expense.category = category
            new_data["category"] = category

        expense.updated_at = datetime.utcnow()

        await self._log_action(
            event_id=expense.event_id,
            user_id=user_id,
            entity_type="expense",
            entity_id=expense.id,
            action=AuditAction.UPDATE,
            old_data=old_data,
            new_data=new_data
        )

        return expense

    async def delete_expense(
            self,
            expense_id: int,
            user_id: int
    ) -> bool:
        """Soft delete an expense."""
        expense = await self.get_expense(expense_id)
        if not expense:
            return False

        expense.is_deleted = True
        expense.deleted_at = datetime.utcnow()
        expense.deleted_by = user_id

        await self._log_action(
            event_id=expense.event_id,
            user_id=user_id,
            entity_type="expense",
            entity_id=expense.id,
            action=AuditAction.DELETE,
            old_data={
                "amount": float(expense.amount),
                "description": expense.description
            }
        )

        return True

    async def can_edit_expense(
            self,
            expense_id: int,
            user_id: int,
            is_event_creator: bool = False
    ) -> bool:
        """
        Check if user can edit an expense.

        Rules:
        - Payer can edit their own expenses
        - Event creator can edit any expense
        """
        if is_event_creator:
            return True

        expense = await self.get_expense(expense_id)
        if not expense:
            return False

        # Check if user is the payer
        payer = expense.payer
        return payer.user_id == user_id if payer.user_id else False

    async def get_expense_summary(
            self,
            event_id: int
    ) -> Dict:
        """
        Get expense summary for an event.

        Returns:
            Dict with:
            - total_amount: Total spent
            - expense_count: Number of expenses
            - by_category: Breakdown by category
            - by_participant: Breakdown by who paid
        """
        expenses = await self.get_event_expenses(event_id)

        total_amount = sum(e.amount for e in expenses)
        expense_count = len(expenses)

        by_category = {}
        by_participant = {}

        for expense in expenses:
            # By category
            category = expense.category or "Без категории"
            if category not in by_category:
                by_category[category] = Decimal(0)
            by_category[category] += expense.amount

            # By participant
            payer_name = expense.payer.display_name
            if payer_name not in by_participant:
                by_participant[payer_name] = Decimal(0)
            by_participant[payer_name] += expense.amount

        return {
            "total_amount": total_amount,
            "expense_count": expense_count,
            "by_category": by_category,
            "by_participant": by_participant
        }

    async def _log_action(
            self,
            event_id: int,
            user_id: int,
            entity_type: str,
            entity_id: int,
            action: AuditAction,
            old_data: Optional[dict] = None,
            new_data: Optional[dict] = None
    ):
        """Log an action to audit log."""
        log = AuditLog(
            event_id=event_id,
            user_id=user_id,
            entity_type=entity_type,
            entity_id=entity_id,
            action=action,
            old_data=old_data,
            new_data=new_data
        )
        self.session.add(log)