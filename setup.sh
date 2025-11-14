#!/bin/bash
# Setup script for News Edit Agent

echo "Setting up News Edit Agent..."

# Create virtual environment
echo "Creating virtual environment..."
python3 -m venv venv

# Activate virtual environment
source venv/bin/activate

# Upgrade pip
echo "Upgrading pip..."
pip install --upgrade pip

# Install dependencies
echo "Installing dependencies..."
pip install -r requirements.txt

# Create data directories
echo "Creating data directories..."
mkdir -p data/proxies
mkdir -p data/thumbnails
mkdir -p data/keyframes
mkdir -p data/outputs

# Copy environment template
if [ ! -f .env ]; then
    echo "Creating .env file..."
    cp .env.example .env
    echo "⚠️  Please edit .env with your Open Arena API credentials"
fi

echo "✓ Setup complete!"
echo ""
echo "Next steps:"
echo "1. Edit .env with your API credentials"
echo "2. Activate virtual environment: source venv/bin/activate"
echo "3. Run ingest: python cli.py ingest --input ./rushes --story 'story-name'"
echo "4. Compile edit: python cli.py compile --story 'story-name' --brief 'description' --duration 90"
