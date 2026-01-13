from datetime import datetime
from typing import List

from sqlalchemy import BigInteger, Boolean, String, Index, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from bot.database.base import Base, TimestampMixin


class Participant(Base, TimestampMixin):
    """Participant in an event."""

    __tablename__ = "participants"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    event_id: Mapped[int] = mapped_column(BigInteger, nullable=False, index=True)
    user_id: Mapped[int | None] = mapped_column(BigInteger, nullable=True)
    username: Mapped[str | None] = mapped_column(String(255), nullable=True)
    display_name: Mapped[str] = mapped_column(String(255), nullable=False)
    participant_type: Mapped[str] = mapped_column(
        String(20),
        nullable=False
    )  # telegram_chat, telegram_external, external
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    added_by: Mapped[int] = mapped_column(BigInteger, nullable=False)
    deleted_at: Mapped[datetime | None] = mapped_column(nullable=True)
    deleted_by: Mapped[int | None] = mapped_column(BigInteger, nullable=True)

    # Relationships
    event: Mapped["Event"] = relationship(
        back_populates="participants",
        foreign_keys=[event_id]
    )
    family_memberships: Mapped[List["FamilyMember"]] = relationship(
        back_populates="participant",
        cascade="all, delete-orphan"
    )
    expenses_paid: Mapped[List["Expense"]] = relationship(
        back_populates="payer",
        foreign_keys="Expense.payer_id"
    )
    expense_splits: Mapped[List["ExpenseSplit"]] = relationship(
        back_populates="participant",
        cascade="all, delete-orphan"
    )
    debts_owed: Mapped[List["DebtSettlement"]] = relationship(
        back_populates="debtor",
        foreign_keys="DebtSettlement.debtor_id"
    )
    debts_to_collect: Mapped[List["DebtSettlement"]] = relationship(
        back_populates="creditor",
        foreign_keys="DebtSettlement.creditor_id"
    )
    families_headed: Mapped[List["Family"]] = relationship(
        back_populates="family_head",
        foreign_keys="Family.family_head_id"
    )

    __table_args__ = (
        Index("idx_event_participant", "event_id", "user_id"),
        Index("idx_participant_active", "event_id", "is_active"),
        Index(
            "uq_event_user_active",
            "event_id",
            "user_id",
            unique=True,
            postgresql_where="user_id IS NOT NULL AND is_active = TRUE"
        ),
    )

    def __repr__(self) -> str:
        return f"<Participant(id={self.id}, name='{self.display_name}')>"