from datetime import datetime
from decimal import Decimal

from sqlalchemy import BigInteger, Boolean, String, Numeric, JSON, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from bot.database.base import Base


class DebtSettlement(Base):
    """Record of debt settlements between participants."""

    __tablename__ = "debt_settlements"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    event_id: Mapped[int] = mapped_column(BigInteger, nullable=False, index=True)
    debtor_id: Mapped[int] = mapped_column(BigInteger, nullable=False, index=True)
    creditor_id: Mapped[int] = mapped_column(BigInteger, nullable=False, index=True)
    amount: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False)
    settled: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    settled_at: Mapped[datetime | None] = mapped_column(nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        server_default=func.now(),
        nullable=False
    )

    # Relationships
    event: Mapped["Event"] = relationship(
        back_populates="debt_settlements",
        foreign_keys=[event_id]
    )
    debtor: Mapped["Participant"] = relationship(
        back_populates="debts_owed",
        foreign_keys=[debtor_id]
    )
    creditor: Mapped["Participant"] = relationship(
        back_populates="debts_to_collect",
        foreign_keys=[creditor_id]
    )

    def __repr__(self) -> str:
        return f"<DebtSettlement(debtor={self.debtor_id}, creditor={self.creditor_id}, amount={self.amount})>"


class AuditLog(Base):
    """Audit log for tracking changes to entities."""

    __tablename__ = "audit_log"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    event_id: Mapped[int | None] = mapped_column(BigInteger, nullable=True, index=True)
    user_id: Mapped[int] = mapped_column(BigInteger, nullable=False, index=True)
    entity_type: Mapped[str] = mapped_column(String(50), nullable=False)
    entity_id: Mapped[int] = mapped_column(BigInteger, nullable=False)
    action: Mapped[str] = mapped_column(String(20), nullable=False)  # create, update, delete
    old_data: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    new_data: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        server_default=func.now(),
        nullable=False,
        index=True
    )

    # Relationships
    event: Mapped["Event"] = relationship(
        back_populates="audit_logs",
        foreign_keys=[event_id]
    )

    def __repr__(self) -> str:
        return f"<AuditLog(entity_type='{self.entity_type}', action='{self.action}', entity_id={self.entity_id})>"