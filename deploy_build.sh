#!/bin/bash

# Build script for Render.com deployment with database preservation
echo "🚀 Starting deployment build process..."

# Install Python dependencies
echo "📦 Installing Python dependencies..."
pip install -r requirements.txt

# Setup data directory if it doesn't exist
if [ ! -d "/opt/render/project/data" ]; then
    echo "📁 Creating data directory for persistent storage..."
    mkdir -p /opt/render/project/data
fi

# Check if database exists in persistent storage
if [ -f "/opt/render/project/data/redirect_tool.db" ]; then
    echo "✅ Found existing database in persistent storage"
    echo "📊 Database info:"
    ls -lah /opt/render/project/data/redirect_tool.db
else
    echo "📝 No existing database found in persistent storage"
    echo "🔨 Database will be created on first run"
fi

# Always build frontend to ensure latest code is deployed
echo "🔨 Building React frontend..."
cd frontend
echo "📦 Installing frontend dependencies..."
npm ci
echo "⚛️ Building React app..."
npm run build
cd ..

echo "✅ Build complete! Application ready to start."