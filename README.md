# Information Retrieval Chatbot

An **end-to-end Information Retrieval (IR) chatbot** that combines Wikipedia data scraping, inverted index creation, query processing, and AI-powered summarization. The system supports both casual conversations using BlenderBot and topic-specific information retrieval with BART-generated summaries.

## 📋 Table of Contents

- [Project Overview](#project-overview)
- [Architecture](#architecture)
- [Features](#features)
- [Technical Stack](#technical-stack)
- [Project Structure](#project-structure)
- [Setup Instructions](#setup-instructions)
- [Usage Guide](#usage-guide)
- [API Endpoints](#api-endpoints)
- [How It Works](#how-it-works)

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
│ Inverted Index  │
│ (TF-IDF Scoring)│
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│ Top-K Documents │
│ Retrieval       │
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
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│  Summary        │
│  Response       │
└─────────────────┘
```

## ✨ Features

### 1. Multi-Threaded Wikipedia Scraper (`project_3_threaded.py`)
- **Parallel Processing**: Uses ThreadPoolExecutor with 10 worker threads
- **Topic Coverage**: Scrapes 6,000+ articles per topic across 10 topics:
  - Health, Technology, Environment, Economy, Entertainment
  - Sports, Politics, Education, Travel, Food
- **Quality Control**: Filters articles with summaries < 200 characters
- **Deduplication**: Tracks visited pages across threads using thread-safe dictionaries
- **Resilience**: Implements retry logic for connection errors and rate limiting
- **Progress Tracking**: Saves intermediate results every 100 articles

### 2. Inverted Index with Skip Pointers (`project_3_indexing.py`)
- **TF-IDF Scoring**: Calculates term frequency-inverse document frequency for ranking
- **Skip Pointers**: Optimizes query processing with skip intervals (√n)
- **Preprocessing**: 
  - Lowercasing
  - Special character removal
  - Stopword removal (NLTK)
  - Porter stemming
- **DAAT Algorithm**: Document-at-a-time AND query processing with skip optimization
- **Efficient Storage**: Linked list structure for postings lists

### 3. Document Mapping (`Doc_id_URL_mapping.py`)
- Creates a mapping from document IDs (Revision IDs) to Wikipedia URLs
- Enables dynamic content fetching for summarization

### 4. Web Application (`app.py`)
- **Framework**: FastAPI for high-performance async API
- **Dual Mode Operation**:
  - **Chit-Chat Mode**: BlenderBot-400M-distill for casual conversation
  - **Query Mode**: Information retrieval with BART summarization
- **Query Processing**:
  - Preprocesses queries (stemming, stopword removal)
  - Retrieves top-k documents using TF-IDF scores
  - Filters documents by selected topic
  - Fetches full content from Wikipedia URLs
  - Generates dynamic summaries using BART
- **Response Tracking**: Logs queries, responses, response times, and topics to `results.json`

### 5. Frontend Interface
- **Framework**: Vanilla JavaScript with Tailwind CSS
- **Features**:
  - Topic selection sidebar
  - Real-time chat interface
  - Loading indicators
  - Responsive design
  - Visualization support (Chart.js integration)

### 6. Analytics & Visualization
- Tracks response times per query
- Monitors documents retrieved per query
- Analyzes topic popularity
- Stores interaction history in JSON format

## 🛠️ Technical Stack

### Backend
- **Python 3.x**
- **FastAPI**: Web framework for API endpoints
- **Transformers (Hugging Face)**:
  - `facebook/blenderbot-400M-distill`: Conversational AI
  - `facebook/bart-large-cnn`: Text summarization
- **NLTK**: Natural language processing (stopwords, stemming)
- **BeautifulSoup4**: HTML parsing for Wikipedia content
- **Requests**: HTTP client for fetching web content
- **Wikipedia API**: Data scraping

### Frontend
- **HTML5/CSS3**: Structure and styling
- **Tailwind CSS**: Utility-first CSS framework
- **JavaScript (ES6+)**: Client-side interactivity
- **Chart.js**: Data visualization (response times, document counts, topic popularity)

### Data Processing
- **Pandas**: Data manipulation (if needed)
- **JSON**: Data serialization
- **Pickle**: Index serialization (optional)

## 📁 Project Structure

```
Information_Retrieval_Project/
│
├── app.py                          # Main FastAPI application
├── project_3_threaded.py           # Multi-threaded Wikipedia scraper
├── project_3_indexing.py           # Inverted index creation with skip pointers
├── Doc_id_URL_mapping.py           # Document ID to URL mapping generator
│
├── templates/
│   └── index.html                  # Frontend HTML template
│
├── static/                         # Static files (CSS, JS)
│   ├── script.js                   # Frontend JavaScript
│   ├── style.css                   # Additional styles
│   └── tailwind.css                # Tailwind CSS compiled
│
├── data/
│   ├── all_topics_wikipedia_data.json    # Scraped Wikipedia data
│   ├── postings_list.json                # Inverted index (TF-IDF)
│   ├── doc_id_to_url.json                # Document ID to URL mapping
│   └── results.json                      # Query results and analytics
│
├── notebooks/
│   ├── dialogpt.ipynb              # DialoGPT experimentation
│   ├── DynaSumm.ipynb              # Dynamic summarization experiments
│   └── visual.ipynb                # Visualization and analytics
│
├── requirements.txt                # Python dependencies
├── package.json                    # Node.js dependencies (Tailwind)
├── tailwind.config.js              # Tailwind configuration
│
└── README.md                       # This file
```

## 🚀 Setup Instructions

### Prerequisites
- Python 3.8+
- Node.js and npm (for Tailwind CSS)
- 8GB+ RAM (for loading ML models)
- Internet connection (for downloading models and scraping)

### Installation

1. **Clone the repository**
   ```bash
   git clone <repository-url>
   cd Information_Retrieval_Project
   ```

2. **Install Python dependencies**
   ```bash
   pip install -r requirements.txt
   ```

3. **Download NLTK data**
   ```python
   import nltk
   nltk.download('stopwords')
   ```

4. **Install Tailwind CSS (optional, for frontend customization)**
   ```bash
   npm install
   ```

5. **Prepare the data** (if not already present):
   
   a. **Scrape Wikipedia data**:
      ```bash
      python project_3_threaded.py
      ```
      This will create `all_topics_wikipedia_data.json` (may take several hours).
   
   b. **Create document mapping**:
      ```bash
      python Doc_id_URL_mapping.py
      ```
      This creates `doc_id_to_url.json`.
   
   c. **Build inverted index**:
      ```bash
      python project_3_indexing.py
      ```
      This creates `postings_list.json` (ensure the data file path is correct).

6. **Verify required files exist**:
   - `all_topics_wikipedia_data.json`
   - `postings_list.json` (or update `app.py` to use `.pkl` if using pickle)
   - `doc_id_to_url.json`

### Running the Application

1. **Start the FastAPI server**:
   ```bash
   uvicorn app:app --reload --host 0.0.0.0 --port 8000
   ```

2. **Access the web interface**:
   Open your browser and navigate to `http://localhost:8000`

3. **For production deployment** (e.g., GCP):
   ```bash
   gunicorn -w 4 -k uvicorn.workers.UvicornWorker app:app
   ```

## 📖 Usage Guide

### Chit-Chat Mode (Default)
1. When the application loads, you're in chit-chat mode
2. Type any casual message (e.g., "Hello!", "How are you?")
3. BlenderBot will respond with conversational replies

### Query Mode
1. **Select a topic** from the left sidebar (e.g., "Technology", "Health")
2. The system switches to query mode
3. **Ask topic-specific questions** (e.g., "Tell me about artificial intelligence")
4. The system will:
   - Preprocess your query
   - Retrieve top-k relevant documents
   - Fetch full content from Wikipedia
   - Generate a summary using BART
   - Display the summary in the chat

### Example Queries
- **Technology**: "What is machine learning?", "Tell me about quantum computing"
- **Health**: "What are the benefits of exercise?", "Explain diabetes"
- **Environment**: "What causes climate change?", "Tell me about renewable energy"
- **Food**: "What is the history of pizza?", "Explain fermentation"

## 🔌 API Endpoints

### `GET /`
- **Description**: Serves the main web interface
- **Response**: HTML page with chat interface

### `POST /api/chat`
- **Description**: Handles chit-chat messages (BlenderBot)
- **Request Body**:
  ```json
  {
    "user_message": "Hello, how are you?"
  }
  ```
- **Response**:
  ```json
  {
    "response": "I'm doing well, thanks for asking!"
  }
  ```

### `POST /api/select_topic`
- **Description**: Selects a topic and switches to query mode
- **Request Body**:
  ```json
  {
    "topic": "Technology"
  }
  ```
- **Response**:
  ```json
  {
    "message": "Topic 'Technology' selected"
  }
  ```

### `POST /api/retrieve_and_summarize`
- **Description**: Retrieves and summarizes documents for a query
- **Request Body**:
  ```json
  {
    "query": "Tell me about artificial intelligence"
  }
  ```
- **Response**:
  ```json
  {
    "summary": "Artificial intelligence (AI) is...",
    "response_time": 5234.56,
    "docs_retrieved_count": 3,
    "topic": "Technology"
  }
  ```

## 🔍 How It Works

### 1. Data Collection Phase
- **Multi-threaded scraping**: 10 threads process topics in parallel
- **Wikipedia API**: Searches for topic-related articles
- **Link following**: Expands search by following article links
- **Quality filtering**: Only keeps articles with substantial summaries (>200 chars)
- **Deduplication**: Prevents duplicate articles across topics

### 2. Indexing Phase
- **Tokenization**: Splits documents into tokens
- **Preprocessing**: Lowercases, removes special chars, stopwords, stems
- **TF-IDF Calculation**:
  - **TF (Term Frequency)**: `count(term) / total_tokens`
  - **IDF (Inverse Document Frequency)**: `log(total_docs / docs_with_term)`
  - **TF-IDF**: `TF × IDF`
- **Skip Pointers**: Adds skip pointers every √n nodes for faster intersection

### 3. Query Processing Phase
- **Query Preprocessing**: Same as document preprocessing
- **Document Retrieval**:
  - Looks up query terms in inverted index
  - Sums TF-IDF scores for matching documents
  - Ranks documents by total score
  - Returns top-k documents
- **Topic Filtering**: Filters retrieved documents by selected topic
- **Content Fetching**: Retrieves full article content from Wikipedia URLs

### 4. Summarization Phase
- **Chunking**: Splits long content into 500-token chunks
- **BART Summarization**: Generates summaries for each chunk
- **Aggregation**: Combines chunk summaries into final response
- **Query-Aware**: Incorporates query context in summary generation

### 5. Response Generation
- **Chit-Chat**: Direct BlenderBot response
- **Query Mode**: BART-generated summary with metadata (response time, doc count)

## 📊 Performance Considerations

- **Index Size**: The inverted index can be large (50,000+ documents)
- **Model Loading**: BlenderBot and BART models are loaded at startup (~2-3GB RAM)
- **Response Times**: 
  - Chit-chat: ~100-500ms
  - Query mode: 2-70 seconds (depends on content fetching and summarization)
- **Caching**: Consider caching frequently accessed documents
- **Parallel Processing**: URL fetching could be parallelized for faster responses

## 🐛 Known Issues & Limitations

1. **Postings List Format**: `app.py` expects `postings_list.json`, but the project may have `postings_list.pkl`. Update the file format or conversion as needed.
2. **Static Files**: Ensure `static/` directory exists with `script.js` and `tailwind.css`
3. **Rate Limiting**: Wikipedia API may rate-limit requests during scraping
4. **Memory Usage**: Large models require significant RAM
5. **Response Time**: URL fetching and summarization can be slow for long articles

## 🔮 Future Enhancements

- [ ] Implement caching for frequently accessed documents
- [ ] Add query expansion and relevance feedback
- [ ] Support multi-topic queries
- [ ] Implement BM25 ranking as an alternative to TF-IDF
- [ ] Add user authentication and session management
- [ ] Deploy with Docker containerization
- [ ] Add more visualization dashboards
- [ ] Implement query history and favorites

## 📝 License

This project is for educational purposes. Please respect Wikipedia's terms of use and rate limits.

## 👥 Contributors

Developed as part of an Information Retrieval course project.

---

**Note**: This project demonstrates the integration of **state-of-the-art conversational AI models** (BlenderBot) and **summarization models** (BART) with a robust information retrieval pipeline to create an engaging and highly functional chatbot.
