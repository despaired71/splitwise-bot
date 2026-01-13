"""Service for managing events."""

from datetime import datetime
from typing import List, Optional

from sqlalchemy import select, and_
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from bot.database.models import Event, Participant, AuditLog
from bot.utils.constants import EventStatus, AuditAction


class EventService:
    """Service for event operations."""

    def __init__(self, session: AsyncSession):
        self.session = session

    async def create_event(
            self,
            name: str,
            creator_id: int,
            description: Optional[str] = None,
            chat_id: Optional[int] = None,
            currency: str = "RUB"
    ) -> Event:
        """
        Create a new event.

        Args:
            name: Event name
            creator_id: Telegram user ID of creator
            description: Optional event description
            chat_id: Optional group chat ID
            currency: Currency code (default: RUB)

        Returns:
            Created event
        """
        event = Event(
            name=name,
            description=description,
            creator_id=creator_id,
            chat_id=chat_id,
            currency=currency,
            status=EventStatus.ACTIVE
        )

        self.session.add(event)
        await self.session.flush()

        # Log creation
        await self._log_action(
            event_id=event.id,
            user_id=creator_id,
            entity_type="event",
            entity_id=event.id,
            action=AuditAction.CREATE,
            new_data={"name": name, "description": description}
        )

        return event

    async def get_event(self, event_id: int) -> Optional[Event]:
        """Get event by ID."""
        result = await self.session.execute(
            select(Event)
            .where(and_(Event.id == event_id, Event.is_deleted == False))
            .options(
                selectinload(Event.participants),
                selectinload(Event.families),
                selectinload(Event.expenses)
            )
        )
        return result.scalar_one_or_none()

    async def get_user_events(
            self,
            user_id: int,
            include_closed: bool = False
    ) -> List[Event]:
        """
        Get all events where user is creator or participant.

        Args:
            user_id: Telegram user ID
            include_closed: Whether to include closed events

        Returns:
            List of events
        """
        query = select(Event).where(Event.is_deleted == False)

        if not include_closed:
            query = query.where(Event.status == EventStatus.ACTIVE)

        # Events where user is creator or participant
        query = query.where(
            (Event.creator_id == user_id) |
            (Event.id.in_(
                select(Participant.event_id)
                .where(and_(
                    Participant.user_id == user_id,
                    Participant.is_active == True
                ))
            ))
        )

        query = query.order_by(Event.created_at.desc())

        result = await self.session.execute(query)
        return list(result.scalars().all())

    async def get_chat_events(self, chat_id: int) -> List[Event]:
        """Get all active events for a chat."""
        result = await self.session.execute(
            select(Event)
            .where(and_(
                Event.chat_id == chat_id,
                Event.status == EventStatus.ACTIVE,
                Event.is_deleted == False
            ))
            .order_by(Event.created_at.desc())
        )
        return list(result.scalars().all())

    async def update_event(
            self,
            event_id: int,
            user_id: int,
            name: Optional[str] = None,
            description: Optional[str] = None
    ) -> Optional[Event]:
        """
        Update event details.

        Args:
            event_id: Event ID
            user_id: User making the change
            name: New name (if changing)
            description: New description (if changing)

        Returns:
            Updated event or None if not found
        """
        event = await self.get_event(event_id)
        if not event:
            return None

        old_data = {"name": event.name, "description": event.description}
        new_data = {}

        if name is not None:
            event.name = name
            new_data["name"] = name

        if description is not None:
            event.description = description
            new_data["description"] = description

        event.updated_at = datetime.utcnow()

        # Log update
        await self._log_action(
            event_id=event.id,
            user_id=user_id,
            entity_type="event",
            entity_id=event.id,
            action=AuditAction.UPDATE,
            old_data=old_data,
            new_data=new_data
        )

        return event

    async def close_event(self, event_id: int, user_id: int) -> Optional[Event]:
        """Close an event."""
        event = await self.get_event(event_id)
        if not event:
            return None

        event.status = EventStatus.CLOSED
        event.closed_at = datetime.utcnow()

        await self._log_action(
            event_id=event.id,
            user_id=user_id,
            entity_type="event",
            entity_id=event.id,
            action=AuditAction.UPDATE,
            old_data={"status": EventStatus.ACTIVE},
            new_data={"status": EventStatus.CLOSED}
        )

        return event

    async def delete_event(self, event_id: int, user_id: int) -> bool:
        """
        Soft delete an event.

        Args:
            event_id: Event ID
            user_id: User performing deletion

        Returns:
            True if deleted, False if not found
        """
        event = await self.get_event(event_id)
        if not event:
            return False

        event.is_deleted = True
        event.deleted_at = datetime.utcnow()

        await self._log_action(
            event_id=event.id,
            user_id=user_id,
            entity_type="event",
            entity_id=event.id,
            action=AuditAction.DELETE,
            old_data={"name": event.name}
        )

        return True

    async def is_creator(self, event_id: int, user_id: int) -> bool:
        """Check if user is event creator."""
        event = await self.get_event(event_id)
        return event is not None and event.creator_id == user_id

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