#!/bin/bash
# Script to disable rate limiting for load testing

echo "🔧 Disabling rate limiting for load testing..."
echo ""

# Check if docker-compose is available
if ! command -v docker-compose &> /dev/null; then
    echo "❌ Error: docker-compose not found"
    exit 1
fi

# Rebuild API container with latest code (needed for rate_limit_enabled feature)
echo "Rebuilding API container with latest code..."
docker-compose build api

# Stop API
echo "Stopping API container..."
docker-compose stop api

# Set environment variable and restart
echo "Setting RATE_LIMIT_ENABLED=false and restarting API..."
RATE_LIMIT_ENABLED=false docker-compose up -d api

echo ""
echo "✅ Rate limiting disabled. API restarted."
echo "   You can now run: make performance-test"
echo ""
echo "⚠️  Remember to re-enable rate limiting after testing:"
echo "   ./scripts/enable_rate_limit.sh"

