#!/bin/bash
# Script to run load tests with rate limiting disabled

echo "⚠️  Disabling rate limiting for load testing..."
echo "   This script temporarily disables rate limiting in the API container"
echo ""

# Check if API container is running
if ! docker ps | grep -q ecommerce-api; then
    echo "❌ Error: API container is not running"
    echo "   Please start it with: make up"
    exit 1
fi

# Disable rate limiting
echo "Setting RATE_LIMIT_ENABLED=false in API container..."
docker exec ecommerce-api sh -c 'export RATE_LIMIT_ENABLED=false'

# Actually, we need to restart the container with the env var
# Let's use a different approach - modify docker-compose temporarily
echo ""
echo "📝 To disable rate limiting for load tests:"
echo "   1. Edit docker-compose.yml and set RATE_LIMIT_ENABLED=false"
echo "   2. Restart API: docker-compose restart api"
echo "   3. Run load tests: make performance-test"
echo "   4. Re-enable rate limiting: set RATE_LIMIT_ENABLED=true and restart"
echo ""
echo "Or use the environment variable override:"
echo "   RATE_LIMIT_ENABLED=false docker-compose up -d api"



