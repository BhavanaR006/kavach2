"""Vercel serverless entry point for Kavach 2.0."""
import sys
import os

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Override database URL for Vercel (use /tmp which is writable)
os.environ.setdefault("DATABASE_URL", "sqlite+aiosqlite:////tmp/kavach.db")

from app.main import app

# Vercel needs the app object
handler = app
