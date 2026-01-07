#!/bin/bash
# Script to re-enable rate limiting after load testing

echo "🔧 Re-enabling rate limiting..."
echo ""

# Check if docker-compose is available
if ! command -v docker-compose &> /dev/null; then
    echo "❌ Error: docker-compose not found"
    exit 1
fi

# Stop API
echo "Stopping API container..."
docker-compose stop api

# Set environment variable and restart
echo "Setting RATE_LIMIT_ENABLED=true and restarting API..."
RATE_LIMIT_ENABLED=true docker-compose up -d api

# Wait for API to be ready
echo "Waiting for API to be ready..."
sleep 3

echo ""
echo "✅ Rate limiting re-enabled. API restarted."

