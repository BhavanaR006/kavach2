#!/bin/bash
echo "Starting Kavach 2.0..."
pip install -r requirements.txt
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
