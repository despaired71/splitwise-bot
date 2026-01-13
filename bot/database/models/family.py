from typing import List

from sqlalchemy import BigInteger, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from bot.database.base import Base, TimestampMixin


class Family(Base, TimestampMixin):
    """Family group within an event."""

    __tablename__ = "families"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    event_id: Mapped[int] = mapped_column(BigInteger, nullable=False, index=True)
    global_family_id: Mapped[int | None] = mapped_column(
        BigInteger,
        nullable=True,
        index=True
    )
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    family_head_id: Mapped[int | None] = mapped_column(BigInteger, nullable=True)

    # Relationships
    event: Mapped["Event"] = relationship(
        back_populates="families",
        foreign_keys=[event_id]
    )
    global_family: Mapped["GlobalFamily"] = relationship(
        back_populates="families",
        foreign_keys=[global_family_id]
    )
    family_head: Mapped["Participant"] = relationship(
        back_populates="families_headed",
        foreign_keys=[family_head_id]
    )
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
    family_id: Mapped[int] = mapped_column(BigInteger, nullable=False)
    participant_id: Mapped[int] = mapped_column(BigInteger, nullable=False)

    # Relationships
    family: Mapped["Family"] = relationship(
        back_populates="members",
        foreign_keys=[family_id]
    )
    participant: Mapped["Participant"] = relationship(
        back_populates="family_memberships",
        foreign_keys=[participant_id]
    )

    __table_args__ = (
        {"sqlite_autoincrement": True},
    )

    def __repr__(self) -> str:
        return f"<FamilyMember(family_id={self.family_id}, participant_id={self.participant_id})>"