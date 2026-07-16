"""
Application configuration via pydantic BaseSettings.

All environment variables are loaded from .env file or system environment.
No secrets are hardcoded.
"""

from pydantic_settings import BaseSettings
from pydantic import Field


class Settings(BaseSettings):
    """Kavach 2.0 application settings loaded from environment."""

    # Anthropic Claude API (paid - optional)
    ANTHROPIC_API_KEY: str = Field(default="", description="Anthropic API key for Claude")

    # Google Gemini API (FREE - recommended for demo)
    GEMINI_API_KEY: str = Field(default="", description="Google Gemini API key (free tier)")

    # Groq API (FREE - fast, reliable alternative)
    GROQ_API_KEY: str = Field(default="", description="Groq API key (free tier, 30 req/min)")

    # WhatsApp Business Cloud API
    WHATSAPP_ACCESS_TOKEN: str = Field(default="", description="Meta WhatsApp access token")
    WHATSAPP_PHONE_NUMBER_ID: str = Field(default="", description="WhatsApp phone number ID")
    WHATSAPP_VERIFY_TOKEN: str = Field(default="kavach_verify_2024", description="Webhook verification token")

    # Twilio SMS fallback
    TWILIO_ACCOUNT_SID: str = Field(default="", description="Twilio account SID")
    TWILIO_AUTH_TOKEN: str = Field(default="", description="Twilio auth token")
    TWILIO_PHONE_NUMBER: str = Field(default="", description="Twilio sender phone number")

    # BHASHINI API
    BHASHINI_API_KEY: str = Field(default="", description="BHASHINI API key")
    BHASHINI_USER_ID: str = Field(default="", description="BHASHINI user ID")

    # Database
    DATABASE_URL: str = Field(
        default="sqlite+aiosqlite:///./kavach.db",
        description="Database connection URL"
    )

    # Application
    ENVIRONMENT: str = Field(default="development", description="Runtime environment")
    LOG_LEVEL: str = Field(default="INFO", description="Logging level")

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        case_sensitive = True


settings = Settings()
