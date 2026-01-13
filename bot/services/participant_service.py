"""Service for managing participants."""

from datetime import datetime
from typing import List, Optional

from sqlalchemy import select, and_, func
from sqlalchemy.ext.asyncio import AsyncSession

from bot.database.models import Participant, Expense, AuditLog
from bot.utils.constants import ParticipantType, AuditAction


class ParticipantService:
    """Service for participant operations."""

    def __init__(self, session: AsyncSession):
        self.session = session

    async def add_participant(
            self,
            event_id: int,
            added_by: int,
            display_name: str,
            participant_type: ParticipantType,
            user_id: Optional[int] = None,
            username: Optional[str] = None
    ) -> Participant:
        """
        Add a participant to an event.

        Args:
            event_id: Event ID
            added_by: User ID who is adding the participant
            display_name: Display name
            participant_type: Type of participant
            user_id: Telegram user ID (if applicable)
            username: Telegram username (if applicable)

        Returns:
            Created participant
        """
        # Check if participant already exists (for Telegram users)
        if user_id:
            existing = await self.get_participant_by_user(event_id, user_id)
            if existing and existing.is_active:
                return existing
            elif existing:
                # Reactivate soft-deleted participant
                existing.is_active = True
                existing.deleted_at = None
                existing.deleted_by = None
                return existing

        participant = Participant(
            event_id=event_id,
            user_id=user_id,
            username=username,
            display_name=display_name,
            participant_type=participant_type,
            added_by=added_by
        )

        self.session.add(participant)
        await self.session.flush()

        # Log creation
        await self._log_action(
            event_id=event_id,
            user_id=added_by,
            entity_type="participant",
            entity_id=participant.id,
            action=AuditAction.CREATE,
            new_data={"display_name": display_name, "participant_type": participant_type}
        )

        return participant

    async def get_participant(self, participant_id: int) -> Optional[Participant]:
        """Get participant by ID."""
        result = await self.session.execute(
            select(Participant)
            .where(and_(
                Participant.id == participant_id,
                Participant.is_active == True
            ))
        )
        return result.scalar_one_or_none()

    async def get_participant_by_user(
            self,
            event_id: int,
            user_id: int
    ) -> Optional[Participant]:
        """Get participant by event and user ID."""
        result = await self.session.execute(
            select(Participant)
            .where(and_(
                Participant.event_id == event_id,
                Participant.user_id == user_id
            ))
        )
        return result.scalar_one_or_none()

    async def get_event_participants(
            self,
            event_id: int,
            active_only: bool = True
    ) -> List[Participant]:
        """Get all participants for an event."""
        query = select(Participant).where(Participant.event_id == event_id)

        if active_only:
            query = query.where(Participant.is_active == True)

        query = query.order_by(Participant.display_name)

        result = await self.session.execute(query)
        return list(result.scalars().all())

    async def update_participant(
            self,
            participant_id: int,
            user_id: int,
            display_name: Optional[str] = None
    ) -> Optional[Participant]:
        """Update participant display name."""
        participant = await self.get_participant(participant_id)
        if not participant:
            return None

        old_data = {"display_name": participant.display_name}

        if display_name is not None:
            participant.display_name = display_name

        await self._log_action(
            event_id=participant.event_id,
            user_id=user_id,
            entity_type="participant",
            entity_id=participant.id,
            action=AuditAction.UPDATE,
            old_data=old_data,
            new_data={"display_name": display_name}
        )

        return participant

    async def delete_participant(
            self,
            participant_id: int,
            user_id: int
    ) -> tuple[bool, Optional[str]]:
        """
        Delete a participant (with validation).

        Args:
            participant_id: Participant ID
            user_id: User performing deletion

        Returns:
            Tuple of (success, error_message)
        """
        participant = await self.get_participant(participant_id)
        if not participant:
            return False, "Участник не найден"

        # Check if participant has expenses
        has_expenses = await self._participant_has_expenses(participant_id)
        if has_expenses:
            return False, "У участника есть расходы. Сначала удалите их."

        # Check if participant is family head
        is_family_head = await self._is_family_head(participant_id)
        if is_family_head:
            return False, "Участник является казначеем семьи. Сначала смените казначея."

        # Soft delete
        participant.is_active = False
        participant.deleted_at = datetime.utcnow()
        participant.deleted_by = user_id

        await self._log_action(
            event_id=participant.event_id,
            user_id=user_id,
            entity_type="participant",
            entity_id=participant.id,
            action=AuditAction.DELETE,
            old_data={"display_name": participant.display_name}
        )

        return True, None

    async def _participant_has_expenses(self, participant_id: int) -> bool:
        """Check if participant has any expenses."""
        result = await self.session.execute(
            select(func.count(Expense.id))
            .where(and_(
                Expense.payer_id == participant_id,
                Expense.is_deleted == False
            ))
        )
        count = result.scalar_one()
        return count > 0

    async def _is_family_head(self, participant_id: int) -> bool:
        """Check if participant is a family head."""
        from bot.database.models import Family

        result = await self.session.execute(
            select(func.count(Family.id))
            .where(Family.family_head_id == participant_id)
        )
        count = result.scalar_one()
        return count > 0

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