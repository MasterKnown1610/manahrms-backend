#!/bin/bash
# Build script for Render deployment

set -e

echo "🔧 Installing build dependencies..."
pip install --upgrade pip setuptools wheel

echo "📦 Installing Python packages..."
pip install --no-cache-dir -r requirements.txt

echo "✅ Build completed successfully!"

