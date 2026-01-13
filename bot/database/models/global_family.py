from datetime import datetime
from typing import List

from sqlalchemy import BigInteger, String, Text, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column, relationship

from bot.database.base import Base, TimestampMixin


class GlobalFamily(Base, TimestampMixin):
    """Global family template that can be reused across events."""

    __tablename__ = "global_families"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    creator_id: Mapped[int] = mapped_column(BigInteger, nullable=False, index=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)

    # Relationships
    members: Mapped[List["GlobalFamilyMember"]] = relationship(
        back_populates="family",
        cascade="all, delete-orphan"
    )
    families: Mapped[List["Family"]] = relationship(
        back_populates="global_family"
    )

    def __repr__(self) -> str:
        return f"<GlobalFamily(id={self.id}, name='{self.name}')>"


class GlobalFamilyMember(Base, TimestampMixin):
    """Member of a global family template."""

    __tablename__ = "global_family_members"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    global_family_id: Mapped[int] = mapped_column(
        BigInteger,
        ForeignKey("global_families.id", ondelete="CASCADE"),
        nullable=False,
        index=True
    )
    user_id: Mapped[int | None] = mapped_column(BigInteger, nullable=True)
    username: Mapped[str | None] = mapped_column(String(255), nullable=True)
    display_name: Mapped[str] = mapped_column(String(255), nullable=False)
    is_family_head: Mapped[bool] = mapped_column(default=False, nullable=False)

    # Relationships
    family: Mapped["GlobalFamily"] = relationship(back_populates="members")

    def __repr__(self) -> str:
        return f"<GlobalFamilyMember(id={self.id}, name='{self.display_name}')>"