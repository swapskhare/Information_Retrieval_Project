#!/bin/bash

# Information Retrieval Chatbot - Setup Script
# This script sets up the development environment

set -e  # Exit on error

echo "🚀 Setting up Information Retrieval Chatbot..."
echo ""

# Check Python version
echo "📋 Checking Python version..."
python_version=$(python3 --version 2>&1 | awk '{print $2}')
required_version="3.8"
if ! python3 -c "import sys; exit(0 if sys.version_info >= (3, 8) else 1)"; then
    echo "❌ Error: Python 3.8+ is required. Found: $python_version"
    exit 1
fi
echo "✅ Python $python_version detected"
echo ""

# Create virtual environment
if [ ! -d "venv" ]; then
    echo "📦 Creating virtual environment..."
    python3 -m venv venv
    echo "✅ Virtual environment created"
else
    echo "✅ Virtual environment already exists"
fi
echo ""

# Activate virtual environment
echo "🔧 Activating virtual environment..."
source venv/bin/activate
echo ""

# Upgrade pip
echo "⬆️  Upgrading pip, setuptools, and wheel..."
pip install --upgrade pip setuptools wheel > /dev/null 2>&1
echo "✅ Pip upgraded"
echo ""

# Install dependencies
echo "📥 Installing Python dependencies..."
pip install -r requirements.txt
echo "✅ Dependencies installed"
echo ""

# Download NLTK data
echo "📚 Downloading NLTK stopwords..."
python -m nltk.downloader stopwords > /dev/null 2>&1 || python -c "import nltk; nltk.download('stopwords')"
echo "✅ NLTK data downloaded"
echo ""

# Check for data files
echo "📊 Checking data files..."
if [ ! -f "data/all_topics_wikipedia_data.json" ]; then
    echo "⚠️  Warning: data/all_topics_wikipedia_data.json not found"
    echo "   Run 'make scrape' or 'python scraper.py' to generate data"
else
    echo "✅ Wikipedia data found"
fi

if [ ! -f "data/postings_list.json" ]; then
    echo "⚠️  Warning: data/postings_list.json not found"
    echo "   Run 'make index' or 'python indexer.py' to build index"
else
    echo "✅ Postings list found"
fi

if [ ! -f "data/doc_id_to_url.json" ]; then
    echo "⚠️  Warning: data/doc_id_to_url.json not found"
    echo "   Run 'make map-docs' or 'python doc_mapper.py' to generate mapping"
else
    echo "✅ Document mapping found"
fi
echo ""

echo "✨ Setup complete!"
echo ""
echo "📝 Next steps:"
echo "   1. Activate virtual environment: source venv/bin/activate"
echo "   2. Run the application: make run"
echo "   3. Open browser: http://localhost:8000"
echo ""
echo "💡 Tip: Use 'make help' to see all available commands"

