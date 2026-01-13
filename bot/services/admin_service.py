"""Service for admin operations."""

from typing import Dict, List, Any
from decimal import Decimal

from sqlalchemy import select, func, and_
from sqlalchemy.ext.asyncio import AsyncSession

from bot.database.models import (
    Event, Participant, Family, Expense,
    GlobalFamily, DebtSettlement, AuditLog
)


class AdminService:
    """Service for admin-only operations."""

    def __init__(self, session: AsyncSession):
        self.session = session

    async def get_system_stats(self) -> Dict[str, Any]:
        """Get overall system statistics."""
        stats = {}

        # Total events
        result = await self.session.execute(
            select(func.count(Event.id))
        )
        stats["total_events"] = result.scalar()

        # Active events
        result = await self.session.execute(
            select(func.count(Event.id))
            .where(and_(Event.status == "active", Event.is_deleted == False))
        )
        stats["active_events"] = result.scalar()

        # Total participants
        result = await self.session.execute(
            select(func.count(Participant.id.distinct()))
        )
        stats["total_participants"] = result.scalar()

        # Unique users (with user_id)
        result = await self.session.execute(
            select(func.count(Participant.user_id.distinct()))
            .where(Participant.user_id.isnot(None))
        )
        stats["unique_users"] = result.scalar()

        # Total expenses
        result = await self.session.execute(
            select(func.count(Expense.id))
            .where(Expense.is_deleted == False)
        )
        stats["total_expenses"] = result.scalar()

        # Total amount tracked
        result = await self.session.execute(
            select(func.sum(Expense.amount))
            .where(Expense.is_deleted == False)
        )
        total_amount = result.scalar()
        stats["total_amount"] = total_amount if total_amount else Decimal(0)

        # Total families
        result = await self.session.execute(
            select(func.count(Family.id))
        )
        stats["total_families"] = result.scalar()

        # Global family templates
        result = await self.session.execute(
            select(func.count(GlobalFamily.id))
        )
        stats["global_families"] = result.scalar()

        return stats

    async def get_all_events(
            self,
            limit: int = 50,
            offset: int = 0,
            include_deleted: bool = False
    ) -> List[Event]:
        """Get all events in the system."""
        query = select(Event).order_by(Event.created_at.desc())

        if not include_deleted:
            query = query.where(Event.is_deleted == False)

        query = query.limit(limit).offset(offset)

        result = await self.session.execute(query)
        return list(result.scalars().all())

    async def get_event_details(self, event_id: int) -> Dict[str, Any]:
        """Get detailed information about an event."""
        result = await self.session.execute(
            select(Event).where(Event.id == event_id)
        )
        event = result.scalar_one_or_none()

        if not event:
            return None

        # Get participants count
        result = await self.session.execute(
            select(func.count(Participant.id))
            .where(and_(
                Participant.event_id == event_id,
                Participant.is_active == True
            ))
        )
        participants_count = result.scalar()

        # Get expenses count and total
        result = await self.session.execute(
            select(
                func.count(Expense.id),
                func.sum(Expense.amount)
            )
            .where(and_(
                Expense.event_id == event_id,
                Expense.is_deleted == False
            ))
        )
        expenses_count, total_amount = result.one()

        # Get families count
        result = await self.session.execute(
            select(func.count(Family.id))
            .where(Family.event_id == event_id)
        )
        families_count = result.scalar()

        return {
            "event": event,
            "participants_count": participants_count,
            "expenses_count": expenses_count or 0,
            "total_amount": total_amount if total_amount else Decimal(0),
            "families_count": families_count
        }

    async def get_user_activity(self, user_id: int) -> Dict[str, Any]:
        """Get activity statistics for a specific user."""
        # Events created
        result = await self.session.execute(
            select(func.count(Event.id))
            .where(Event.creator_id == user_id)
        )
        events_created = result.scalar()

        # Events participated
        result = await self.session.execute(
            select(func.count(Participant.event_id.distinct()))
            .where(Participant.user_id == user_id)
        )
        events_participated = result.scalar()

        # Expenses added
        result = await self.session.execute(
            select(func.count(Expense.id))
            .join(Participant, Expense.payer_id == Participant.id)
            .where(and_(
                Participant.user_id == user_id,
                Expense.is_deleted == False
            ))
        )
        expenses_added = result.scalar()

        # Total paid
        result = await self.session.execute(
            select(func.sum(Expense.amount))
            .join(Participant, Expense.payer_id == Participant.id)
            .where(and_(
                Participant.user_id == user_id,
                Expense.is_deleted == False
            ))
        )
        total_paid = result.scalar()

        return {
            "user_id": user_id,
            "events_created": events_created,
            "events_participated": events_participated,
            "expenses_added": expenses_added,
            "total_paid": total_paid if total_paid else Decimal(0)
        }

    async def get_recent_activity(self, limit: int = 20) -> List[AuditLog]:
        """Get recent activity across the system."""
        result = await self.session.execute(
            select(AuditLog)
            .order_by(AuditLog.created_at.desc())
            .limit(limit)
        )
        return list(result.scalars().all())

    async def delete_event_permanently(self, event_id: int) -> bool:
        """Permanently delete an event and all related data."""
        result = await self.session.execute(
            select(Event).where(Event.id == event_id)
        )
        event = result.scalar_one_or_none()

        if not event:
            return False

        await self.session.delete(event)
        return True

    async def restore_deleted_event(self, event_id: int) -> bool:
        """Restore a soft-deleted event."""
        result = await self.session.execute(
            select(Event).where(Event.id == event_id)
        )
        event = result.scalar_one_or_none()

        if not event:
            return False

        event.is_deleted = False
        event.deleted_at = None
        return True

    async def get_top_spenders(self, limit: int = 10) -> List[Dict[str, Any]]:
        """Get top spenders across all events."""
        result = await self.session.execute(
            select(
                Participant.display_name,
                Participant.user_id,
                func.count(Expense.id).label("expense_count"),
                func.sum(Expense.amount).label("total_amount")
            )
            .join(Expense, Participant.id == Expense.payer_id)
            .where(Expense.is_deleted == False)
            .group_by(Participant.id, Participant.display_name, Participant.user_id)
            .order_by(func.sum(Expense.amount).desc())
            .limit(limit)
        )

        spenders = []
        for row in result:
            spenders.append({
                "name": row.display_name,
                "user_id": row.user_id,
                "expense_count": row.expense_count,
                "total_amount": row.total_amount
            })

        return spenders

    async def get_events_by_creator(self, creator_id: int) -> List[Event]:
        """Get all events created by a specific user."""
        result = await self.session.execute(
            select(Event)
            .where(Event.creator_id == creator_id)
            .order_by(Event.created_at.desc())
        )
        return list(result.scalars().all())