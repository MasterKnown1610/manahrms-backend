#!/bin/bash

# Simple script to run FastAPI app
# Usage: ./run.sh

# Activate virtual environment
source venv/bin/activate

# Run the FastAPI server
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000

