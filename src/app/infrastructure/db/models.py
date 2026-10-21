from datetime import date, datetime
from decimal import Decimal
from uuid import UUID

from sqlalchemy import CheckConstraint, DateTime, Index, MetaData, Numeric, String, text
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


class Base(DeclarativeBase):
    """Declarative base with predictable constraint names for migrations"""

    metadata = MetaData(
        naming_convention={
            "pk": "pk_%(table_name)s",
            "uq": "uq_%(table_name)s_%(column_0_N_name)s",
            "ix": "ix_%(table_name)s_%(column_0_N_name)s",
            "ck": "ck_%(table_name)s_%(constraint_name)s",
        }
    )


class RateORM(Base):
    """Official NBRB rate: rate BYN for scale units of the currency"""

    __tablename__ = "rates"

    currency_code: Mapped[str] = mapped_column(String(3), primary_key=True)
    rate_date: Mapped[date] = mapped_column(primary_key=True)
    scale: Mapped[int]
    rate: Mapped[Decimal] = mapped_column(Numeric(12, 4))


class DealORM(Base):
    """Exchange deal row, mapped to and from domain Deal in repositories"""

    __tablename__ = "deals"
    __table_args__ = (
        CheckConstraint("status IN ('pending', 'accepted', 'declined')", name="status_valid"),
        CheckConstraint("amount > 0", name="amount_positive"),
        Index(
            "ix_deals_pending_created_at",
            "created_at",
            postgresql_where=text("status = 'pending'"),
        ),
        Index(
            "ix_deals_accepted_resolved_at",
            "resolved_at",
            postgresql_where=text("status = 'accepted'"),
        ),
    )

    id: Mapped[UUID] = mapped_column(primary_key=True)
    amount: Mapped[Decimal] = mapped_column(Numeric(20, 2))
    from_currency: Mapped[str] = mapped_column(String(3))
    to_currency: Mapped[str] = mapped_column(String(3))
    rate: Mapped[Decimal] = mapped_column(Numeric)
    converted_amount: Mapped[Decimal] = mapped_column(Numeric(20, 2))
    status: Mapped[str] = mapped_column(String(16))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    resolved_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
