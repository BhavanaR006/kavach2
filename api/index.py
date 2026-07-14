"""
Vercel serverless entry point for Kavach 2.0.

Exports the FastAPI app instance for Vercel's Python runtime.
Vercel automatically wraps it with Mangum-like ASGI handling.
"""

from app.main import app

# Vercel expects the FastAPI/ASGI app here
app = app
