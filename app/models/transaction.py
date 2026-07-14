"""
Transaction model and schemas for Kavach 2.0.

Tracks UPI payment intents, their risk assessment status,
and final disposition (completed, blocked, flagged).
"""

from datetime import datetime, timezone
from enum import Enum
from typing import Optional

from pydantic import BaseModel, Field
from sqlalchemy import Column, Integer, String, Float, DateTime, Enum as SAEnum

from app.db.database import Base


class TransactionStatus(str, Enum):
    """Possible states of a tracked transaction."""
    PENDING = "PENDING"
    FLAGGED = "FLAGGED"
    COMPLETED = "COMPLETED"
    BLOCKED = "BLOCKED"


class RiskLevel(str, Enum):
    """Risk classification levels."""
    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"
    CRITICAL = "CRITICAL"


class Transaction(Base):
    """SQLAlchemy model for UPI transaction tracking."""

    __tablename__ = "transactions"

    id: int = Column(Integer, primary_key=True, autoincrement=True)
    user_phone: str = Column(String(20), nullable=False, index=True)
    recipient_phone: str = Column(String(20), nullable=False)
    amount: float = Column(Float, nullable=False)
    initiated_at: datetime = Column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
    )
    status: str = Column(
        SAEnum(TransactionStatus),
        default=TransactionStatus.PENDING,
        nullable=False,
    )
    risk_score: int = Column(Integer, default=0)
    risk_level: str = Column(
        SAEnum(RiskLevel),
        default=RiskLevel.LOW,
        nullable=True,
    )
    created_at: datetime = Column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
    )

    def __repr__(self) -> str:
        return (
            f"<Transaction(id={self.id}, user={self.user_phone}, "
            f"amount={self.amount}, status={self.status})>"
        )


# --- Pydantic Schemas ---


class TransactionCreate(BaseModel):
    """Schema for creating a new transaction."""
    user_phone: str = Field(..., description="User's phone in E.164 format", examples=["+919999999999"])
    recipient_phone: str = Field(..., description="Recipient's phone/UPI ID", examples=["+918888888888"])
    amount: float = Field(..., gt=0, description="Transaction amount in INR", examples=[40000.0])

    class Config:
        json_schema_extra = {
            "example": {
                "user_phone": "+919999999999",
                "recipient_phone": "+918888888888",
                "amount": 40000.0,
            }
        }


class TransactionResponse(BaseModel):
    """Schema for transaction API responses."""
    id: int
    user_phone: str
    recipient_phone: str
    amount: float
    initiated_at: datetime
    status: TransactionStatus
    risk_score: int
    risk_level: Optional[RiskLevel] = None
    created_at: datetime

    class Config:
        from_attributes = True
