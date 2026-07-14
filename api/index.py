"""
Vercel serverless entry point for Kavach 2.0.

Exports the FastAPI app instance for Vercel's Python runtime.
Vercel automatically wraps it with Mangum-like ASGI handling.
"""

import sys
import os

# Add project root to path so 'app' package is importable
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.main import app

# Vercel expects the FastAPI/ASGI app here
app = app
