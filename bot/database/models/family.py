from typing import List

from sqlalchemy import BigInteger, String, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column, relationship

from bot.database.base import Base, TimestampMixin


class Family(Base, TimestampMixin):
    """Family group within an event."""

    __tablename__ = "families"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    event_id: Mapped[int] = mapped_column(
        BigInteger,
        ForeignKey("events.id", ondelete="CASCADE"),
        nullable=False,
        index=True
    )
    global_family_id: Mapped[int | None] = mapped_column(
        BigInteger,
        ForeignKey("global_families.id", ondelete="SET NULL"),
        nullable=True,
        index=True
    )
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    family_head_id: Mapped[int | None] = mapped_column(
        BigInteger,
        ForeignKey("participants.id", ondelete="SET NULL"),
        nullable=True
    )

    # Relationships
    event: Mapped["Event"] = relationship(back_populates="families")
    global_family: Mapped["GlobalFamily"] = relationship(back_populates="families")
    family_head: Mapped["Participant"] = relationship(back_populates="families_headed")
    members: Mapped[List["FamilyMember"]] = relationship(
        back_populates="family",
        cascade="all, delete-orphan"
    )
    expense_splits: Mapped[List["ExpenseSplit"]] = relationship(
        back_populates="family",
        cascade="all, delete-orphan"
    )

    def __repr__(self) -> str:
        return f"<Family(id={self.id}, name='{self.name}')>"


class FamilyMember(Base, TimestampMixin):
    """Member of a family within an event."""

    __tablename__ = "family_members"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    family_id: Mapped[int] = mapped_column(
        BigInteger,
        ForeignKey("families.id", ondelete="CASCADE"),
        nullable=False
    )
    participant_id: Mapped[int] = mapped_column(
        BigInteger,
        ForeignKey("participants.id", ondelete="CASCADE"),
        nullable=False
    )

    # Relationships
    family: Mapped["Family"] = relationship(back_populates="members")
    participant: Mapped["Participant"] = relationship(back_populates="family_memberships")

    def __repr__(self) -> str:
        return f"<FamilyMember(family_id={self.family_id}, participant_id={self.participant_id})>"