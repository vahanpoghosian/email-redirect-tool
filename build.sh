#!/bin/bash

# Build script for Render.com deployment
echo "🔨 Building React frontend..."

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

echo "✅ Build complete! React app built and ready to deploy."