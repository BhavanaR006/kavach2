"""
Scam pattern storage and seeding for Kavach 2.0.

Maintains a database of known scam patterns across categories
and languages, seeded from data/scam_patterns.json.
"""

import json
from pathlib import Path
from datetime import datetime, timezone

from sqlalchemy import Column, Integer, String, DateTime, Text
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from loguru import logger

from app.db.database import Base


class ScamPattern(Base):
    """SQLAlchemy model for storing known scam patterns."""

    __tablename__ = "scam_patterns"

    id: int = Column(Integer, primary_key=True, autoincrement=True)
    pattern_text: str = Column(Text, nullable=False)
    pattern_type: str = Column(String(50), nullable=False, index=True)
    language: str = Column(String(10), nullable=False, default="en")
    severity: str = Column(String(20), nullable=False, default="HIGH")
    source: str = Column(String(100), nullable=True)
    created_at: datetime = Column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
    )

    def __repr__(self) -> str:
        return f"<ScamPattern(id={self.id}, type={self.pattern_type}, lang={self.language})>"


# Valid pattern types
PATTERN_TYPES = [
    "AUTHORITY_IMPERSONATION",
    "URGENCY",
    "ISOLATION",
    "FINANCIAL_DEMAND",
    "DIGITAL_ARREST",
    "KYC_FRAUD",
]


async def seed_patterns(session: AsyncSession) -> int:
    """
    Seed scam patterns from data/scam_patterns.json into the database.

    Args:
        session: Active async database session.

    Returns:
        Number of patterns inserted.
    """
    # Check if patterns already exist
    result = await session.execute(select(ScamPattern).limit(1))
    if result.scalar_one_or_none() is not None:
        logger.info("Scam patterns already seeded, skipping")
        return 0

    # Load patterns from JSON file
    patterns_file = Path(__file__).parent.parent.parent / "data" / "scam_patterns.json"
    if not patterns_file.exists():
        logger.warning(f"Scam patterns file not found: {patterns_file}")
        return 0

    with open(patterns_file, "r", encoding="utf-8") as f:
        patterns_data = json.load(f)

    count = 0
    for pattern in patterns_data.get("patterns", []):
        scam_pattern = ScamPattern(
            pattern_text=pattern["text"],
            pattern_type=pattern["type"],
            language=pattern.get("language", "en"),
            severity=pattern.get("severity", "HIGH"),
            source=pattern.get("source", "I4C Database"),
        )
        session.add(scam_pattern)
        count += 1

    await session.commit()
    logger.info(f"Seeded {count} scam patterns into database")
    return count


async def get_patterns_by_type(
    session: AsyncSession, pattern_type: str
) -> list[ScamPattern]:
    """
    Retrieve all scam patterns of a given type.

    Args:
        session: Active async database session.
        pattern_type: One of the PATTERN_TYPES constants.

    Returns:
        List of matching ScamPattern records.
    """
    result = await session.execute(
        select(ScamPattern).where(ScamPattern.pattern_type == pattern_type)
    )
    return list(result.scalars().all())


async def get_patterns_by_language(
    session: AsyncSession, language: str
) -> list[ScamPattern]:
    """
    Retrieve all scam patterns for a given language.

    Args:
        session: Active async database session.
        language: Language code (en, hi, te, ta, bn).

    Returns:
        List of matching ScamPattern records.
    """
    result = await session.execute(
        select(ScamPattern).where(ScamPattern.language == language)
    )
    return list(result.scalars().all())
