from datetime import datetime
from decimal import Decimal
from typing import List

from sqlalchemy import BigInteger, Boolean, String, Text, Numeric, CheckConstraint, Index
from sqlalchemy.orm import Mapped, mapped_column, relationship

from bot.database.base import Base, TimestampMixin


class Expense(Base, TimestampMixin):
    """Expense entry for an event."""

    __tablename__ = "expenses"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    event_id: Mapped[int] = mapped_column(BigInteger, nullable=False, index=True)
    payer_id: Mapped[int] = mapped_column(BigInteger, nullable=False, index=True)
    amount: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=False)
    category: Mapped[str | None] = mapped_column(String(100), nullable=True)
    split_type: Mapped[str] = mapped_column(
        String(20),
        nullable=False
    )  # equal, custom, specific
    is_deleted: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    deleted_at: Mapped[datetime | None] = mapped_column(nullable=True)
    deleted_by: Mapped[int | None] = mapped_column(BigInteger, nullable=True)

    # Relationships
    event: Mapped["Event"] = relationship(
        back_populates="expenses",
        foreign_keys=[event_id]
    )
    payer: Mapped["Participant"] = relationship(
        back_populates="expenses_paid",
        foreign_keys=[payer_id]
    )
    splits: Mapped[List["ExpenseSplit"]] = relationship(
        back_populates="expense",
        cascade="all, delete-orphan"
    )

    __table_args__ = (
        Index("idx_event_expense", "event_id", "is_deleted"),
        Index("idx_expense_created", "created_at"),
    )

    def __repr__(self) -> str:
        return f"<Expense(id={self.id}, amount={self.amount}, description='{self.description}')>"


class ExpenseSplit(Base):
    """How an expense is split among participants or families."""

    __tablename__ = "expense_splits"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    expense_id: Mapped[int] = mapped_column(BigInteger, nullable=False, index=True)
    participant_id: Mapped[int | None] = mapped_column(
        BigInteger,
        nullable=True,
        index=True
    )
    family_id: Mapped[int | None] = mapped_column(BigInteger, nullable=True, index=True)
    share_amount: Mapped[Decimal | None] = mapped_column(Numeric(12, 2), nullable=True)
    share_percentage: Mapped[Decimal | None] = mapped_column(
        Numeric(5, 2),
        nullable=True
    )

    # Relationships
    expense: Mapped["Expense"] = relationship(
        back_populates="splits",
        foreign_keys=[expense_id]
    )
    participant: Mapped["Participant"] = relationship(
        back_populates="expense_splits",
        foreign_keys=[participant_id]
    )
    family: Mapped["Family"] = relationship(
        back_populates="expense_splits",
        foreign_keys=[family_id]
    )

    __table_args__ = (
        CheckConstraint(
            "(participant_id IS NOT NULL) OR (family_id IS NOT NULL)",
            name="check_participant_or_family"
        ),
        CheckConstraint(
            "(participant_id IS NULL) OR (family_id IS NULL)",
            name="check_not_both"
        ),
    )

    def __repr__(self) -> str:
        target = f"participant={self.participant_id}" if self.participant_id else f"family={self.family_id}"
        return f"<ExpenseSplit(expense_id={self.expense_id}, {target})>"