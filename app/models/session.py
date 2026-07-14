"""
Conversation session model and schemas for Kavach 2.0.

Tracks multi-turn conversations between the agent and users,
including message history, detection state, and risk assessment.
"""

from datetime import datetime, timezone
from enum import Enum
from typing import Optional

from pydantic import BaseModel
from sqlalchemy import Column, Integer, String, DateTime, JSON, ForeignKey

from app.db.database import Base


class SessionState(str, Enum):
    """State machine states for detection flow."""
    IDLE = "IDLE"
    TRANSACTION_DETECTED = "TRANSACTION_DETECTED"
    QUESTIONING = "QUESTIONING"
    CONFIRMED_SAFE = "CONFIRMED_SAFE"
    CONFIRMED_RISK = "CONFIRMED_RISK"
    RECOVERY_IN_PROGRESS = "RECOVERY_IN_PROGRESS"
    RESOLVED = "RESOLVED"


class ConversationSession(Base):
    """SQLAlchemy model for tracking conversation sessions."""

    __tablename__ = "conversation_sessions"

    id: int = Column(Integer, primary_key=True, autoincrement=True)
    user_phone: str = Column(String(20), nullable=False, index=True)
    state: str = Column(String(30), default=SessionState.IDLE, nullable=False)
    transaction_id: int = Column(Integer, ForeignKey("transactions.id"), nullable=True)
    messages: list = Column(JSON, default=list, nullable=False)
    risk_score: int = Column(Integer, default=0)
    risk_level: str = Column(String(20), nullable=True)
    created_at: datetime = Column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
    )
    updated_at: datetime = Column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
        nullable=False,
    )

    def add_message(self, role: str, content: str) -> None:
        """
        Add a message to the conversation history.

        Args:
            role: Message sender role (user, agent, system).
            content: Message text content.
        """
        if self.messages is None:
            self.messages = []
        self.messages = [
            *self.messages,
            {
                "role": role,
                "content": content,
                "timestamp": datetime.now(timezone.utc).isoformat(),
            },
        ]

    def get_message_count(self) -> int:
        """Return total number of messages in this session."""
        return len(self.messages) if self.messages else 0

    def __repr__(self) -> str:
        return (
            f"<ConversationSession(id={self.id}, user={self.user_phone}, "
            f"state={self.state})>"
        )


# --- Pydantic Schemas ---


class SessionResponse(BaseModel):
    """Schema for session API responses."""
    id: int
    user_phone: str
    state: SessionState
    transaction_id: Optional[int] = None
    messages: list
    risk_score: int
    risk_level: Optional[str] = None
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True
