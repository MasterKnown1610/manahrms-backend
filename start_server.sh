#!/bin/bash

# HRMS Backend Startup Script

echo "=================================================="
echo "🚀 Starting HRMS Backend Server"
echo "=================================================="

# Check if virtual environment exists
if [ ! -d "venv" ]; then
    echo "❌ Virtual environment not found!"
    echo "Creating virtual environment..."
    python3 -m venv venv
    source venv/bin/activate
    pip install -r requirements.txt
else
    echo "✅ Virtual environment found"
    source venv/bin/activate
fi

echo ""
echo "📊 Database Configuration:"
echo "   Host: localhost"
echo "   Port: 5432"
echo "   Database: HRMS"
echo "   User: postgres"
echo ""

# Test database connection
echo "Testing database connection..."
python test_connection.py

if [ $? -eq 0 ]; then
    echo ""
    echo "=================================================="
    echo "🎉 Starting FastAPI Server..."
    echo "=================================================="
    echo ""
    echo "📖 API Documentation: http://localhost:8000/docs"
    echo "🔗 API Base URL: http://localhost:8000/api/v1"
    echo ""
    echo "Available Endpoints:"
    echo "  POST /api/v1/auth/register - Register new user"
    echo "  POST /api/v1/auth/login    - Login user"
    echo "  GET  /api/v1/auth/me       - Get current user"
    echo ""
    echo "Press Ctrl+C to stop the server"
    echo "=================================================="
    echo ""
    
    # Start the server using venv's uvicorn
    python -m uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
else
    echo ""
    echo "❌ Database connection failed!"
    echo "Please check:"
    echo "  1. PostgreSQL is running"
    echo "  2. Database 'HRMS' exists"
    echo "  3. Credentials are correct"
    echo ""
    echo "To create the database, run:"
    echo '  psql -U postgres -c "CREATE DATABASE \\"HRMS\\";"'
fi

