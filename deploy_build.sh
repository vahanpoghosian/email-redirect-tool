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

# Build frontend if needed
echo "🔨 Checking React frontend..."
if [ -d "frontend/build" ] && [ -f "frontend/build/index.html" ]; then
    echo "✅ React build files already exist, skipping npm build"
else
    echo "📦 React build not found, building..."

    # Navigate to frontend directory
    cd frontend

    # Install dependencies
    echo "📦 Installing frontend dependencies..."
    npm ci --only=production

    # Build React app
    echo "⚛️ Building React app..."
    npm run build

    # Return to main directory
    cd ..
fi

echo "✅ Build complete! Application ready to start."