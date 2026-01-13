from datetime import datetime
from typing import List

from sqlalchemy import BigInteger, Boolean, String, Text, Index
from sqlalchemy.orm import Mapped, mapped_column, relationship

from bot.database.base import Base, TimestampMixin


class Event(Base, TimestampMixin):
    """Event/gathering where expenses are tracked."""

    __tablename__ = "events"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    creator_id: Mapped[int] = mapped_column(BigInteger, nullable=False, index=True)
    chat_id: Mapped[int | None] = mapped_column(BigInteger, nullable=True, index=True)
    status: Mapped[str] = mapped_column(
        String(20),
        default="active",
        nullable=False,
        index=True
    )  # active, closed, archived
    currency: Mapped[str] = mapped_column(String(3), default="RUB", nullable=False)
    is_deleted: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    closed_at: Mapped[datetime | None] = mapped_column(nullable=True)
    deleted_at: Mapped[datetime | None] = mapped_column(nullable=True)

    # Relationships
    participants: Mapped[List["Participant"]] = relationship(
        back_populates="event",
        cascade="all, delete-orphan"
    )
    families: Mapped[List["Family"]] = relationship(
        back_populates="event",
        cascade="all, delete-orphan"
    )
    expenses: Mapped[List["Expense"]] = relationship(
        back_populates="event",
        cascade="all, delete-orphan"
    )
    debt_settlements: Mapped[List["DebtSettlement"]] = relationship(
        back_populates="event",
        cascade="all, delete-orphan"
    )
    audit_logs: Mapped[List["AuditLog"]] = relationship(
        back_populates="event",
        cascade="all, delete-orphan"
    )

    __table_args__ = (
        Index("idx_event_active", "is_deleted", "status"),
    )

    def __repr__(self) -> str:
        return f"<Event(id={self.id}, name='{self.name}', status='{self.status}')>"