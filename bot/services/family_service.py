"""Service for managing families."""

from typing import List, Optional, Dict

from sqlalchemy import select, and_
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from bot.database.models import (
    Family, FamilyMember, Participant,
    GlobalFamily, GlobalFamilyMember, AuditLog
)
from bot.utils.constants import AuditAction


class FamilyService:
    """Service for family operations."""

    def __init__(self, session: AsyncSession):
        self.session = session

    # ===== Global Family Templates =====

    async def create_global_family(
            self,
            creator_id: int,
            name: str,
            description: Optional[str] = None
    ) -> GlobalFamily:
        """Create a global family template."""
        family = GlobalFamily(
            creator_id=creator_id,
            name=name,
            description=description
        )

        self.session.add(family)
        await self.session.flush()

        return family

    async def add_global_family_member(
            self,
            global_family_id: int,
            display_name: str,
            user_id: Optional[int] = None,
            username: Optional[str] = None,
            is_family_head: bool = False
    ) -> GlobalFamilyMember:
        """Add a member to global family template."""
        member = GlobalFamilyMember(
            global_family_id=global_family_id,
            user_id=user_id,
            username=username,
            display_name=display_name,
            is_family_head=is_family_head
        )

        self.session.add(member)
        await self.session.flush()

        return member

    async def get_global_family(
            self,
            global_family_id: int
    ) -> Optional[GlobalFamily]:
        """Get global family by ID."""
        result = await self.session.execute(
            select(GlobalFamily)
            .where(GlobalFamily.id == global_family_id)
            .options(selectinload(GlobalFamily.members))
        )
        return result.scalar_one_or_none()

    async def get_user_global_families(
            self,
            creator_id: int
    ) -> List[GlobalFamily]:
        """Get all global families created by user."""
        result = await self.session.execute(
            select(GlobalFamily)
            .where(GlobalFamily.creator_id == creator_id)
            .order_by(GlobalFamily.name)
        )
        return list(result.scalars().all())

    async def update_global_family(
            self,
            global_family_id: int,
            name: Optional[str] = None,
            description: Optional[str] = None
    ) -> Optional[GlobalFamily]:
        """Update global family details."""
        family = await self.get_global_family(global_family_id)
        if not family:
            return None

        if name is not None:
            family.name = name

        if description is not None:
            family.description = description

        return family

    async def delete_global_family(
            self,
            global_family_id: int
    ) -> bool:
        """Delete a global family template."""
        family = await self.get_global_family(global_family_id)
        if not family:
            return False

        await self.session.delete(family)
        return True

    # ===== Event Families =====

    async def create_family(
            self,
            event_id: int,
            name: str,
            family_head_id: Optional[int] = None,
            global_family_id: Optional[int] = None,
            user_id: Optional[int] = None
    ) -> Family:
        """Create a family within an event."""
        family = Family(
            event_id=event_id,
            global_family_id=global_family_id,
            name=name,
            family_head_id=family_head_id
        )

        self.session.add(family)
        await self.session.flush()

        # Log creation
        if user_id:
            await self._log_action(
                event_id=event_id,
                user_id=user_id,
                entity_type="family",
                entity_id=family.id,
                action=AuditAction.CREATE,
                new_data={"name": name}
            )

        return family

    async def create_family_from_template(
            self,
            event_id: int,
            global_family_id: int,
            user_id: int
    ) -> Optional[Family]:
        """
        Create event family from global template.

        This will:
        1. Create the family in the event
        2. Add all members from template as participants (if not exist)
        3. Link them to the family
        """
        global_family = await self.get_global_family(global_family_id)
        if not global_family:
            return None

        # Create family
        family = await self.create_family(
            event_id=event_id,
            name=global_family.name,
            global_family_id=global_family_id,
            user_id=user_id
        )

        # Add members
        from bot.services.participant_service import ParticipantService
        from bot.utils.constants import ParticipantType

        participant_service = ParticipantService(self.session)
        family_head_participant_id = None

        for member in global_family.members:
            # Add as participant if not exists
            if member.user_id:
                participant = await participant_service.get_participant_by_user(
                    event_id, member.user_id
                )
                if not participant:
                    participant = await participant_service.add_participant(
                        event_id=event_id,
                        added_by=user_id,
                        display_name=member.display_name,
                        participant_type=ParticipantType.TELEGRAM_EXTERNAL,
                        user_id=member.user_id,
                        username=member.username
                    )
            else:
                # External participant
                participant = await participant_service.add_participant(
                    event_id=event_id,
                    added_by=user_id,
                    display_name=member.display_name,
                    participant_type=ParticipantType.EXTERNAL
                )

            # Add to family
            await self.add_family_member(family.id, participant.id)

            # Track family head
            if member.is_family_head:
                family_head_participant_id = participant.id

        # Set family head
        if family_head_participant_id:
            family.family_head_id = family_head_participant_id

        return family

    async def add_family_member(
            self,
            family_id: int,
            participant_id: int
    ) -> FamilyMember:
        """Add a participant to a family."""
        # Check if already exists
        existing = await self.session.execute(
            select(FamilyMember)
            .where(and_(
                FamilyMember.family_id == family_id,
                FamilyMember.participant_id == participant_id
            ))
        )

        if existing.scalar_one_or_none():
            return existing.scalar_one()

        member = FamilyMember(
            family_id=family_id,
            participant_id=participant_id
        )

        self.session.add(member)
        await self.session.flush()

        return member

    async def remove_family_member(
            self,
            family_id: int,
            participant_id: int
    ) -> bool:
        """Remove a participant from a family."""
        result = await self.session.execute(
            select(FamilyMember)
            .where(and_(
                FamilyMember.family_id == family_id,
                FamilyMember.participant_id == participant_id
            ))
        )

        member = result.scalar_one_or_none()
        if not member:
            return False

        await self.session.delete(member)
        return True

    async def get_family(self, family_id: int) -> Optional[Family]:
        """Get family by ID."""
        result = await self.session.execute(
            select(Family)
            .where(Family.id == family_id)
            .options(
                selectinload(Family.members).selectinload(FamilyMember.participant),
                selectinload(Family.family_head)
            )
        )
        return result.scalar_one_or_none()

    async def get_event_families(self, event_id: int) -> List[Family]:
        """Get all families for an event."""
        result = await self.session.execute(
            select(Family)
            .where(Family.event_id == event_id)
            .options(
                selectinload(Family.members).selectinload(FamilyMember.participant),
                selectinload(Family.family_head)
            )
            .order_by(Family.name)
        )
        return list(result.scalars().all())

    async def update_family(
            self,
            family_id: int,
            user_id: int,
            name: Optional[str] = None,
            family_head_id: Optional[int] = None
    ) -> Optional[Family]:
        """Update family details."""
        family = await self.get_family(family_id)
        if not family:
            return None

        old_data = {"name": family.name, "family_head_id": family.family_head_id}
        new_data = {}

        if name is not None:
            family.name = name
            new_data["name"] = name

        if family_head_id is not None:
            family.family_head_id = family_head_id
            new_data["family_head_id"] = family_head_id

        await self._log_action(
            event_id=family.event_id,
            user_id=user_id,
            entity_type="family",
            entity_id=family.id,
            action=AuditAction.UPDATE,
            old_data=old_data,
            new_data=new_data
        )

        return family

    async def delete_family(
            self,
            family_id: int,
            user_id: int
    ) -> bool:
        """Delete a family from event."""
        family = await self.get_family(family_id)
        if not family:
            return False

        await self._log_action(
            event_id=family.event_id,
            user_id=user_id,
            entity_type="family",
            entity_id=family.id,
            action=AuditAction.DELETE,
            old_data={"name": family.name}
        )

        await self.session.delete(family)
        return True

    async def get_participant_family(
            self,
            event_id: int,
            participant_id: int
    ) -> Optional[Family]:
        """Get family that participant belongs to in an event."""
        result = await self.session.execute(
            select(Family)
            .join(FamilyMember, Family.id == FamilyMember.family_id)
            .where(and_(
                Family.event_id == event_id,
                FamilyMember.participant_id == participant_id
            ))
        )
        return result.scalar_one_or_none()

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