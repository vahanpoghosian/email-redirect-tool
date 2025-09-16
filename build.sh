#!/bin/bash

# Build script for Render.com deployment
echo "🔨 Checking React frontend..."

# Check if React build already exists
if [ -d "frontend/build" ] && [ -f "frontend/build/index.html" ]; then
    echo "✅ React build files already exist, skipping npm build"
else
    echo "📦 React build not found, building..."

    # Navigate to frontend directory
    cd frontend

    # Install dependencies
    echo "📦 Installing dependencies..."
    npm ci --only=production

    # Build React app
    echo "⚛️ Building React app..."
    npm run build

    # Return to main directory
    cd ..
fi

echo "✅ Build setup complete! Flask app ready to serve React files."