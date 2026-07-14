"""
User model and schemas for Kavach 2.0.

Stores user profile information including language preference,
trusted contact details, and demographic risk factors.
"""

from datetime import datetime, timezone
from typing import Optional

from pydantic import BaseModel, Field
from sqlalchemy import Column, Integer, String, Boolean, DateTime

from app.db.database import Base


class User(Base):
    """SQLAlchemy model for Kavach user profiles."""

    __tablename__ = "users"

    id: int = Column(Integer, primary_key=True, autoincrement=True)
    phone: str = Column(String(20), unique=True, nullable=False, index=True)
    name: str = Column(String(100), nullable=True)
    language_preference: str = Column(String(10), default="hi", nullable=False)
    trusted_contact_phone: str = Column(String(20), nullable=True)
    trusted_contact_name: str = Column(String(100), nullable=True)
    age: int = Column(Integer, nullable=True)
    is_first_time_user: bool = Column(Boolean, default=True)
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

    def __repr__(self) -> str:
        return f"<User(id={self.id}, phone={self.phone}, name={self.name})>"


# --- Pydantic Schemas ---


class UserCreate(BaseModel):
    """Schema for creating a new user."""
    phone: str = Field(..., description="Phone in E.164 format", examples=["+919999999999"])
    name: Optional[str] = Field(None, description="User's display name")
    language_preference: str = Field(default="hi", description="Preferred language code")
    trusted_contact_phone: Optional[str] = Field(None, description="Trusted contact phone")
    trusted_contact_name: Optional[str] = Field(None, description="Trusted contact name")
    age: Optional[int] = Field(None, ge=1, le=120, description="User's age")
    is_first_time_user: bool = Field(default=True, description="First-time digital user flag")


class UserResponse(BaseModel):
    """Schema for user API responses."""
    id: int
    phone: str
    name: Optional[str] = None
    language_preference: str
    trusted_contact_phone: Optional[str] = None
    trusted_contact_name: Optional[str] = None
    age: Optional[int] = None
    is_first_time_user: bool
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class UserUpdate(BaseModel):
    """Schema for updating user profile."""
    name: Optional[str] = None
    language_preference: Optional[str] = None
    trusted_contact_phone: Optional[str] = None
    trusted_contact_name: Optional[str] = None
    age: Optional[int] = Field(None, ge=1, le=120)
    is_first_time_user: Optional[bool] = None
