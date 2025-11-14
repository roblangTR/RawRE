#!/bin/bash
# Test Runner Script

echo "=================================="
echo "NEWS EDIT AGENT - TEST SUITE"
echo "=================================="
echo ""

# Check if pytest is installed
if ! command -v pytest &> /dev/null; then
    echo "❌ pytest not found. Installing test dependencies..."
    pip install -r requirements.txt
fi

echo "Running tests..."
echo ""

# Run all tests with coverage
pytest tests/ \
    -v \
    --tb=short \
    --disable-warnings \
    -p no:warnings

echo ""
echo "=================================="
echo "Test run complete!"
echo "=================================="
