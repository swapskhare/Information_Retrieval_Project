# Information Retrieval Chatbot

An **end-to-end Information Retrieval (IR) chatbot** that combines Wikipedia data scraping, inverted index creation, query processing, and AI-powered summarization. The system supports both casual conversations using BlenderBot and topic-specific information retrieval with BART-generated summaries.

## ⚡ Quick Start

Get up and running in minutes!

### Prerequisites Check

```bash
python3 --version  # Should be 3.8+
which make         # Optional, for Makefile commands
```

### Fastest Setup (3 Commands)

```bash
# 1. Setup environment
./setup.sh  # or: make setup

# 2. Activate virtual environment
source venv/bin/activate

# 3. Run application
make run
```

That's it! Open `http://localhost:8000` in your browser! 🎉

> **Note**: If data files are missing, see [Data Setup](#-data-setup) section below.

## 📋 Table of Contents

- [Quick Start](#-quick-start)
- [Project Overview](#-project-overview)
- [Features](#-features)
  - [Core Components](#core-components)
  - [Topics Covered](#topics-covered)
- [Project Structure](#-project-structure)
- [Setup Instructions](#-setup-instructions)
- [Data Setup](#-data-setup)
- [Running the Application](#-running-the-application)
- [Usage Guide](#-usage-guide)
- [API Documentation](#-api-documentation)
- [Architecture](#-architecture)
- [Development](#-development)
- [Technical Stack](#-technical-stack)
- [Performance](#-performance)
- [Troubleshooting](#-troubleshooting)

## 🎯 Project Overview

This project implements a sophisticated information retrieval system that:

1. **Scrapes** Wikipedia articles across 10 diverse topics (50,000+ documents)
2. **Indexes** documents using an inverted index with TF-IDF scoring and skip pointers
3. **Retrieves** relevant documents based on user queries using vector space model
4. **Summarizes** retrieved content using BART (Bidirectional and Auto-Regressive Transformers)
5. **Engages** users in casual conversation using BlenderBot when no topic is selected

The system operates in two modes:
- **Chit-Chat Mode**: General conversation using BlenderBot (default)
- **Query Mode**: Topic-specific information retrieval with summarization (after topic selection)

## ✨ Features

### Core Components

- **Multi-Threaded Wikipedia Scraper** (`scraper.py`)
  - Parallel processing with 10 worker threads
  - Scrapes 6,000+ articles per topic across 10 topics
  - Quality control and deduplication
  - Progress tracking and error handling

- **Inverted Index Builder** (`indexer.py`)
  - TF-IDF scoring for document ranking
  - Skip pointers for optimized query processing
  - Porter stemming and stopword removal
  - DAAT algorithm implementation

- **Document Mapper** (`doc_mapper.py`)
  - Maps document IDs to Wikipedia URLs
  - Enables dynamic content fetching

- **Web Application** (`app.py`)
  - FastAPI-based REST API
  - Dual-mode operation (chit-chat + query)
  - Real-time summarization with BART
  - Query complexity analysis (dynamically retrieves 1-5 documents)
  - Response tracking and analytics
  - GPU/CPU automatic detection with manual override
  - Background model loading with status tracking

### Topics Covered

Health, Technology, Environment, Economy, Entertainment, Sports, Politics, Education, Travel, Food

## 📁 Project Structure

```
Information_Retrieval_Project/
│
├── app.py                    # Main FastAPI application
├── scraper.py                # Wikipedia data scraper
├── indexer.py                # Inverted index builder
├── doc_mapper.py             # Document ID to URL mapper
│
├── Makefile                  # Build automation
├── setup.sh                  # Setup script
├── requirements.txt          # Python dependencies
├── pyproject.toml            # Black code formatter configuration
├── tailwind.config.js        # Tailwind CSS configuration
├── package.json              # Node.js dependencies (Tailwind CSS)
├── .env.example              # Environment variables template
│
├── templates/
│   └── index.html            # Frontend HTML template
│
├── static/                   # Static files
│   ├── script.js             # Frontend JavaScript
│   ├── style.css             # Additional styles
│   └── tailwind.css          # Tailwind CSS
│
├── data/                     # Data files
│   ├── all_topics_wikipedia_data.json
│   ├── postings_list.json
│   ├── doc_id_to_url.json
│   └── results.json
│
├── notebooks/                # Jupyter notebooks
│   ├── dialogpt.ipynb
│   ├── DynaSumm.ipynb
│   └── visual.ipynb
│
└── README.md                 # This file
```

## 🚀 Setup Instructions

### Prerequisites

- **Python 3.8+** (check with `python3 --version`)
- **8GB+ RAM** (for loading ML models)
- **Internet connection** (for downloading models and scraping)
- **Node.js & npm** (optional, for Tailwind CSS customization)

### Automated Setup (Recommended)

**Option 1: Using setup script**
```bash
chmod +x setup.sh
./setup.sh
```

**Option 2: Using Makefile**
```bash
make setup
```

**Option 3: Manual setup**
```bash
# Create virtual environment
python3 -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install --upgrade pip setuptools wheel
pip install -r requirements.txt

# Download NLTK data
python -m nltk.downloader stopwords
```

### Verify Installation

```bash
# Activate virtual environment
source venv/bin/activate

# Check installation
python -c "import fastapi, transformers, nltk; print('✅ All dependencies installed')"
```

## 📊 Data Setup

The application requires three data files in the `data/` directory. **These files are included in the repository** for convenience:

1. **Wikipedia Data** (`all_topics_wikipedia_data.json`) - Scraped Wikipedia articles (7.9MB)
2. **Postings List** (`postings_list.json`) - TF-IDF inverted index (generated from scraped data)
3. **Document Mapping** (`doc_id_to_url.json`) - Document ID to URL mapping (404KB)

> ✅ **Note**: The scraped data and generated indexes are tracked in git, so you can use the project immediately without generating data.

### Option 1: Use Existing Data (Recommended)

If data files are already present in `data/` (they should be if you cloned the repo), you're ready to go! Skip to [Running the Application](#-running-the-application).

### Option 2: Regenerate Data

If you need to regenerate the data files:

**Build all data files:**
```bash
make build-data
```

**Or build individually:**
```bash
# 1. Scrape Wikipedia (takes several hours)
make scrape
# or: python scraper.py

# 2. Build inverted index
make index
# or: python indexer.py

# 3. Generate document mapping
make map-docs
# or: python doc_mapper.py
```

> ⚠️ **Warning**: Scraping Wikipedia data can take 6-12 hours depending on your connection speed.

## 🏃 Running the Application

### Development Mode

```bash
# Activate virtual environment
source venv/bin/activate

# Run with auto-reload
make run
# or: uvicorn app:app --reload --host 0.0.0.0 --port 8000
```

Access at: `http://localhost:8000`

### Production Mode

```bash
make run-prod
# or: gunicorn -w 4 -k uvicorn.workers.UvicornWorker app:app --bind 0.0.0.0:8000
```

### Common Commands

```bash
make help      # See all available commands
make run       # Start development server
make clean     # Clean cache files
make scrape    # Scrape Wikipedia data
make index     # Build inverted index
make map-docs  # Generate document mapping
```

## 📖 Usage Guide

### Chit-Chat Mode (Default)

1. Open the application in your browser
2. Type any casual message (e.g., "Hello!", "How are you?")
3. BlenderBot responds with conversational replies

### Query Mode

1. **Select a topic** from the left sidebar (e.g., "Technology", "Health")
2. The system switches to query mode (selected topic is highlighted in blue)
3. **Ask topic-specific questions** (e.g., "Tell me about artificial intelligence")
4. The system analyzes query complexity and retrieves 1-5 relevant documents
5. **View analytics** in the right sidebar showing response times, documents retrieved, and topic popularity
6. **Deselect topic** by clicking the same topic button again to return to chit-chat mode

### Example Queries

- **Technology**: "What is machine learning?", "Tell me about quantum computing"
- **Health**: "What are the benefits of exercise?", "Explain diabetes"
- **Environment**: "What causes climate change?", "Tell me about renewable energy"
- **Food**: "What is the history of pizza?", "Explain fermentation"

## 🔌 API Documentation

### Endpoints

#### `GET /`
Serves the main web interface.

#### `POST /api/chat`
Handles chit-chat messages using BlenderBot.

**Request:**
```json
{
  "user_message": "Hello, how are you?"
}
```

**Response:**
```json
{
  "response": "I'm doing well, thanks for asking!"
}
```

#### `POST /api/select_topic`
Selects a topic and switches to query mode.

**Request:**
```json
{
  "topic": "Technology"
}
```

**Response:**
```json
{
  "message": "Topic 'Technology' selected"
}
```

#### `POST /api/deselect_topic`
Deselects the current topic and returns to chit-chat mode.

**Request:**
No body required.

**Response:**
```json
{
  "message": "Returned to chit-chat mode"
}
```

#### `GET /api/status`
Returns the loading status of models and data.

**Response:**
```json
{
  "loading": false,
  "progress": "Ready!",
  "loaded": true
}
```

#### `POST /api/retrieve_and_summarize`
Retrieves and summarizes documents for a query. The system automatically determines query complexity and retrieves 1-5 documents accordingly.

**Request:**
```json
{
  "query": "Tell me about artificial intelligence"
}
```

**Response:**
```json
{
  "summary": "Artificial intelligence (AI) is...",
  "response_time": 5.234,
  "docs_retrieved_count": 3,
  "topic": "Technology"
}
```

**Note**: The number of documents retrieved (1-5) is determined automatically based on query complexity. Simple queries retrieve fewer documents, while complex queries retrieve more.

## 🏗️ Architecture

```
┌─────────────────┐
│   User Query    │
└────────┬────────┘
         │
         ▼
┌─────────────────┐      ┌──────────────────┐
│  Topic Selected?│ NO   │  BlenderBot      │
│                 ├─────►│  (Chit-Chat)     │
└────────┬────────┘      └──────────────────┘
         │ YES
         ▼
┌─────────────────┐
│ Query Preprocess│
│ (Stemming,      │
│  Stopword       │
│  Removal)       │
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│ Query Complexity│
│ Analysis        │
│ (Determine 1-5  │
│  documents)     │
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│ Inverted Index  │
│ (TF-IDF Scoring)│
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│ Top-K Documents │
│ Retrieval       │
│ (Filtered by    │
│  Topic)         │
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│ URL Content     │
│ Fetching        │
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│ BART            │
│ Summarization   │
│ (Dynamic length)│
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│  Summary        │
│  Response +     │
│  Analytics      │
└─────────────────┘
```

## 🛠️ Development

### Available Commands

```bash
make help          # Show all available commands
make setup         # Complete setup
make setup-fresh   # Recreate venv from scratch
make install       # Install dependencies only
make run           # Run development server
make run-cpu       # Run in CPU-only mode (FORCE_CPU=1)
make run-prod      # Run production server
make scrape        # Scrape Wikipedia data
make index         # Build inverted index
make map-docs      # Generate document mapping
make build-data    # Build all data files
make clean         # Remove cache files
make lint          # Run pylint on Python files
make format        # Format code with black
make format-check  # Check code formatting without changes
```

### Code Structure

- **`app.py`**: Main FastAPI application with API endpoints
- **`scraper.py`**: Multi-threaded Wikipedia scraper
- **`indexer.py`**: Inverted index creation with TF-IDF
- **`doc_mapper.py`**: Document ID to URL mapping generator

### Environment Variables

Copy `.env.example` to `.env` and configure:

```bash
cp .env.example .env
# Edit .env with your settings
```

**Available Environment Variables:**
- `FORCE_CPU=1`: Force CPU-only mode (useful if GPU is unavailable or to reduce memory usage)
  ```bash
  FORCE_CPU=1 make run
  # or
  make run-cpu
  ```

## 🛠️ Technical Stack

### Backend
- **Python 3.8+**
- **FastAPI**: Web framework
- **Transformers**: BlenderBot & BART models
- **NLTK**: NLP processing
- **BeautifulSoup4**: HTML parsing
- **Wikipedia API**: Data scraping

### Frontend
- **HTML5/CSS3**
- **Tailwind CSS**: Styling
- **JavaScript (ES6+)**: Interactivity
- **Chart.js**: Visualizations

## 📊 Performance

- **Model Loading**: 
  - ~2-3GB RAM (BlenderBot + BART)
  - Models load in background on startup
  - Loading progress tracked via `/api/status` endpoint
- **Response Times**:
  - Chit-chat: ~100-500ms
  - Query mode: 2-70 seconds (depends on query complexity and number of documents)
- **Index Size**: ~50,000+ documents
- **Query Processing**:
  - Simple queries: 1-2 documents retrieved (~2-10 seconds)
  - Medium queries: 2-3 documents retrieved (~10-30 seconds)
  - Complex queries: 3-5 documents retrieved (~30-70 seconds)

## 🐛 Troubleshooting

### Common Issues

1. **Missing data files**
   ```bash
   make build-data
   ```
   Or ensure these files exist in `data/`:
   - `all_topics_wikipedia_data.json`
   - `postings_list.json`
   - `doc_id_to_url.json`

2. **NLTK data not found**
   ```bash
   python -m nltk.downloader stopwords
   ```

3. **Port 8000 already in use**
   ```bash
   # Option 1: Kill existing process
   lsof -ti:8000 | xargs kill -9
   
   # Option 2: Use different port
   uvicorn app:app --reload --port 8001
   ```

4. **Module not found errors**
   ```bash
   # Ensure virtual environment is activated
   source venv/bin/activate
   
   # Reinstall dependencies
   pip install -r requirements.txt
   ```

5. **Memory errors**
   - Ensure 8GB+ RAM available
   - Close other applications
   - Use CPU-only mode: `make run-cpu` or `FORCE_CPU=1 make run`

6. **Models still loading**
   - Wait for the loading overlay to disappear
   - Check status: `curl http://localhost:8000/api/status`
   - Models load in background; server accepts connections immediately

7. **GPU not detected**
   - System automatically falls back to CPU
   - To explicitly use CPU: `make run-cpu`
   - GPU detection happens automatically on startup

### Next Steps After Setup

1. **Wait for models to load** - A loading overlay will appear until models are ready
2. **Try chit-chat mode** (default) - Start a casual conversation with BlenderBot
3. **Select a topic** from the sidebar to switch to query mode
4. **Ask topic-specific questions** - Get AI-powered summaries with automatic complexity analysis
5. **View analytics** - Check the right sidebar for response time trends, documents retrieved, and topic popularity
6. **Deselect topic** - Click the same topic button again to return to chit-chat mode
7. **Check query history** - View `data/results.json` for all queries, responses, and response times

## 📝 License

This project is for educational purposes. Please respect Wikipedia's terms of use and rate limits.

## 👥 Contributors

Developed as part of an Information Retrieval course project.

---
