import requests
from bs4 import BeautifulSoup
from transformers import pipeline, BlenderbotTokenizer, BlenderbotForConditionalGeneration
from fastapi import FastAPI, Request, HTTPException
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from pydantic import BaseModel
import json
from collections import defaultdict
from nltk.stem import PorterStemmer
import re
import time
import nltk
import os
import torch

# Preload nltk stopwords
nltk.download("stopwords", quiet=True)
stop_words = set(nltk.corpus.stopwords.words("english"))

# Detect GPU availability
# Check if CPU-only mode is forced via environment variable
force_cpu = os.getenv("FORCE_CPU", "0").lower() in ("1", "true", "yes")

if force_cpu:
    device = -1
    device_name = "CPU"
    device_type = "CPU"
    print("🔧 CPU-only mode forced via FORCE_CPU environment variable")
elif torch.cuda.is_available():
    device = 0
    device_name = torch.cuda.get_device_name(0)
    device_type = "GPU"
else:
    device = -1
    device_name = "CPU"
    device_type = "CPU"
print(f"🚀 Using device: {device_name} ({device_type})")

# Initialize FastAPI
app = FastAPI()

# Load templates and static files
app.mount("/static", StaticFiles(directory="static"), name="static")
templates = Jinja2Templates(directory="templates")

# Global variables for models (will be loaded on startup)
blenderbot_tokenizer = None
blenderbot_model = None
summarizer = None

# Global variables for data (will be loaded on startup)
postings_list = None
documents = None
doc_id_to_topic = None
doc_id_to_url = None

# Global state for selected topic and chit-chat mode
selected_topic = {"topic": None}
chit_chat_mode = {"active": True}

# Preprocess text function
ps = PorterStemmer()


def preprocess_text(text):
    """
    Preprocess the query text.
    """
    text = text.lower()
    text = re.sub(r"[^a-z0-9\s]", " ", text)
    text = re.sub(r"\s+", " ", text).strip()
    tokens = text.split()
    tokens = [ps.stem(word) for word in tokens if word not in stop_words]
    return tokens


# Retrieve documents based on query
def retrieve_top_docs(query_terms, postings_list, top_k=3):
    """
    Retrieve the top-k documents based on query terms.
    """
    query_terms = preprocess_text(query_terms)  # Preprocess the query
    scores = defaultdict(float)

    for term in query_terms:
        if term in postings_list:
            postings = postings_list[term]
            for entry in postings:
                scores[entry["doc_id"]] += entry["tf_idf"]

    # Sort by score and return top-k document IDs
    sorted_docs = sorted(scores.items(), key=lambda x: x[1], reverse=True)
    return [doc_id for doc_id, _ in sorted_docs[:top_k]]


# Fetch content from a URL
def fetch_url_content(url, timeout=10):
    try:
        # Wikipedia requires a User-Agent header to avoid 403 errors
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"
        }
        response = requests.get(url, timeout=timeout, headers=headers)
        response.raise_for_status()
        soup = BeautifulSoup(response.text, "html.parser")
        paragraphs = soup.find_all("p")
        content = " ".join([para.get_text() for para in paragraphs])
        content = content.strip()
        if len(content) < 100:  # If content is too short, might be an error page
            print(f"⚠️  Warning: Fetched content is very short ({len(content)} chars) for {url}")
        return content
    except requests.exceptions.Timeout:
        print(f"⏱️  Timeout fetching URL: {url}")
        return ""
    except requests.exceptions.RequestException as e:
        print(f"❌ Error fetching the URL {url}: {e}")
        return ""
    except Exception as e:
        print(f"❌ Unexpected error fetching URL {url}: {e}")
        return ""


# Split text into chunks
def chunk_text(text, max_tokens=500):
    words = text.split()
    for i in range(0, len(words), max_tokens):
        yield " ".join(words[i : i + max_tokens])


# Generate a dynamic summary
def generate_dynamic_summary(content, query, max_summary_length=200):
    """
    Generate a concise summary of content relevant to the query.

    Args:
        content: The text content to summarize
        query: The search query to focus the summary on
        max_summary_length: Maximum length of the final summary in words

    Returns:
        A concise summary string
    """
    if summarizer is None:
        raise HTTPException(
            status_code=503, detail="Summarization model is still loading. Please wait."
        )

    # Limit content length to avoid overly long summaries
    # Take first 2000 words of content to keep processing manageable
    content_words = content.split()
    if len(content_words) > 2000:
        content = " ".join(content_words[:2000])

    input_text = f"Query: {query}\n\nContent: {content}"
    chunks = list(chunk_text(input_text, max_tokens=500))

    # Limit to first 3 chunks to avoid overly long summaries
    chunks = chunks[:3]

    summaries = []
    for chunk in chunks:
        try:
            # Generate shorter summaries per chunk
            summary = summarizer(chunk, max_length=100, min_length=30, do_sample=False)
            summaries.append(summary[0]["summary_text"])
        except Exception as e:
            print(f"Error generating summary for chunk: {e}")
            continue

    # Combine summaries and limit total length
    combined_summary = " ".join(summaries)
    summary_words = combined_summary.split()

    if len(summary_words) > max_summary_length:
        combined_summary = " ".join(summary_words[:max_summary_length])
        # Add ellipsis if truncated
        if len(summary_words) > max_summary_length:
            combined_summary += "..."

    return combined_summary


class ChatRequest(BaseModel):
    user_message: str


@app.post("/api/chat")
async def chat(request: ChatRequest):
    # If chit-chat mode is active, respond using BlenderBot
    if chit_chat_mode["active"]:
        if blenderbot_tokenizer is None or blenderbot_model is None:
            raise HTTPException(status_code=503, detail="Models are still loading. Please wait.")

        inputs = blenderbot_tokenizer(request.user_message, return_tensors="pt")
        # Move inputs to the same device as the model
        if device >= 0:
            inputs = {k: v.to(f"cuda:{device}") for k, v in inputs.items()}
        # If CPU, inputs stay on CPU (default)
        reply_ids = blenderbot_model.generate(**inputs)
        bot_response = blenderbot_tokenizer.decode(reply_ids[0], skip_special_tokens=True)
        return {"response": bot_response}
    else:
        # If chit-chat mode is disabled, prompt user to select a topic
        return {"response": "Please select a topic to continue."}


class TopicRequest(BaseModel):
    topic: str


@app.post("/api/select_topic")
async def select_topic(request: TopicRequest):
    # Set the selected topic and disable chit-chat mode
    selected_topic["topic"] = request.topic
    chit_chat_mode["active"] = False
    print(f"Topic selected: {request.topic}")
    return {"message": f"Topic '{request.topic}' selected"}


class QueryRequest(BaseModel):
    query: str


@app.post("/api/retrieve_and_summarize")
async def retrieve_and_summarize(request: QueryRequest):
    if postings_list is None or summarizer is None:
        raise HTTPException(status_code=503, detail="Models are still loading. Please wait.")

    if chit_chat_mode["active"]:
        raise HTTPException(status_code=400, detail="Please select a topic before querying.")

    topic = selected_topic["topic"]
    if not topic:
        raise HTTPException(status_code=400, detail="No topic selected.")

    # Retrieve relevant documents (get more candidates to ensure we find topic matches)
    query = request.query
    start_time = time.time()
    print(f"🔍 Query: '{query}' for topic: '{topic}'")
    # Get top 50 candidates first, then filter by topic
    relevant_doc_ids = retrieve_top_docs(query, postings_list, top_k=50)
    print(f"📊 Retrieved {len(relevant_doc_ids)} candidate documents")

    # Filter documents by topic (efficient lookup)
    topic_filtered_ids = []
    for doc_id in relevant_doc_ids:
        if doc_id in doc_id_to_topic and doc_id_to_topic[doc_id] == topic:
            topic_filtered_ids.append(doc_id)

    print(f"🎯 Found {len(topic_filtered_ids)} documents matching topic '{topic}'")

    # Take top 3 from topic-filtered results
    topic_filtered_ids = topic_filtered_ids[:3]
    print(f"📝 Processing top {len(topic_filtered_ids)} documents")

    if not topic_filtered_ids:
        end_time = time.time()  # Measure end time for no summaries
        response_time = (end_time - start_time) * 1000  # Calculate response time in milliseconds
        result = {
            "summary": f"No relevant documents found for the query that match the selected topic '{topic}'."
        }
        # save_query_to_json(query, result["summary"], topic)  # Save the result
        save_query_to_json(query, result["summary"], response_time, topic)  # Save the result

        return result

    # Generate summaries for relevant documents
    processed_doc_ids = set()
    top_summaries = []
    max_total_summary_length = 500  # Maximum total words across all summaries

    for doc_id in set(topic_filtered_ids):
        if doc_id in processed_doc_ids:
            continue
        processed_doc_ids.add(doc_id)

        # JSON keys are strings, so convert doc_id to string for lookup
        url = doc_id_to_url.get(str(doc_id)) if doc_id_to_url else None
        if not url:
            print(f"⚠️  No URL found for doc_id {doc_id}")
            continue

        print(f"📄 Fetching content from URL for doc_id {doc_id}: {url[:80]}...")
        url_content = fetch_url_content(url)
        if not url_content:
            print(f"⚠️  No content fetched from URL for doc_id {doc_id}")
            continue

        print(f"✅ Fetched {len(url_content)} characters for doc_id {doc_id}, generating summary...")
        try:
            # Generate summary with per-document limit
            dynamic_summary = generate_dynamic_summary(url_content, query, max_summary_length=150)
            if dynamic_summary:
                top_summaries.append(dynamic_summary)
                print(
                    f"✅ Generated summary for doc_id {doc_id} ({len(dynamic_summary.split())} words)"
                )
            else:
                print(f"⚠️  Empty summary generated for doc_id {doc_id}")
        except Exception as e:
            print(f"❌ Error generating summary for doc_id {doc_id}: {e}")
            continue

    if not top_summaries:
        end_time = time.time()  # Measure end time for no summaries
        response_time = (end_time - start_time) * 1000  # Calculate response time in milliseconds
        result = {"summary": "No relevant content found for the query."}
        save_query_to_json(query, result["summary"], response_time, topic)  # Save the result
        return result

    # Combine summaries and limit total length
    summary = " ".join(top_summaries)
    summary_words = summary.split()

    if len(summary_words) > max_total_summary_length:
        summary = " ".join(summary_words[:max_total_summary_length])
        summary += "..."
        print(f"📝 Truncated summary from {len(summary_words)} to {max_total_summary_length} words")

    # Measure response time
    end_time = time.time()
    response_time = (end_time - start_time) * 1000
    result = {
        "summary": summary,
        "response_time": response_time,
        "docs_retrieved_count": len(topic_filtered_ids),
        "topic": topic,
    }

    save_query_to_json(query, summary, response_time, topic)  # Save the result
    return result


def save_query_to_json(query, result, response_time, topic):
    """
    Save the query, its result, and response time to results.json.
    """
    file_path = "data/results.json"
    if os.path.exists(file_path):
        with open(file_path, "r") as file:
            data = json.load(file)
    else:
        data = {}

    # Update query-result pair with response time
    data[query] = {"result": result, "response_time": response_time, "topic": topic}

    with open(file_path, "w") as file:
        json.dump(data, file, indent=4)


# Loading state
models_loading = {"status": True, "progress": "Initializing..."}
models_loaded = False


def load_models_background():
    """
    Load all models and data in the background.
    This is a synchronous function that runs in a thread.
    """
    global blenderbot_tokenizer, blenderbot_model, summarizer
    global postings_list, documents, doc_id_to_topic, doc_id_to_url
    global models_loaded, models_loading

    try:
        models_loading["status"] = True
        models_loading["progress"] = "Loading BlenderBot tokenizer..."
        print("⏳ Loading models and data...")

        # Load models
        print("  📥 Loading BlenderBot tokenizer...")
        blenderbot_tokenizer = BlenderbotTokenizer.from_pretrained(
            "facebook/blenderbot-400M-distill"
        )

        models_loading["progress"] = "Loading BlenderBot model..."
        print("  📥 Loading BlenderBot model...")
        blenderbot_model = BlenderbotForConditionalGeneration.from_pretrained(
            "facebook/blenderbot-400M-distill"
        )
        if device >= 0:
            blenderbot_model = blenderbot_model.to(f"cuda:{device}")
            print(f"  ✅ BlenderBot model moved to {device_type}: {device_name}")
        else:
            blenderbot_model = blenderbot_model.to("cpu")
            print(f"  ✅ BlenderBot model loaded on {device_type}")

        models_loading["progress"] = "Loading BART summarizer..."
        print("  📥 Loading BART summarizer...")
        # device=-1 means CPU, device=0 means GPU
        summarizer = pipeline("summarization", model="facebook/bart-large-cnn", device=device)
        print(f"  ✅ BART summarizer loaded on {device_type}")

        # Load data files
        models_loading["progress"] = "Loading postings list..."
        print("  📥 Loading postings list...")
        with open("data/postings_list.json", "r") as f:
            postings_list = json.load(f)

        models_loading["progress"] = "Loading documents..."
        print("  📥 Loading documents...")
        with open("data/all_topics_wikipedia_data.json", "r") as f:
            documents_data = json.load(f)

        # Create a flat list of documents with doc_id mapping
        documents = []
        doc_id_to_topic = {}
        doc_id = 0
        for topic, records in documents_data.items():
            for record in records:
                documents.append(
                    {
                        "id": doc_id,
                        "title": record["Title"],
                        "summary": record["Summary"],
                        "url": record["URL"],
                        "topic": topic,
                    }
                )
                doc_id_to_topic[doc_id] = topic
                doc_id += 1

        models_loading["progress"] = "Loading document mappings..."
        print("  📥 Loading document URL mapping...")
        with open("data/doc_id_to_url.json", "r") as f:
            doc_id_to_url = json.load(f)

        models_loaded = True
        models_loading["status"] = False
        models_loading["progress"] = "Ready!"
        print("✅ All models and data loaded successfully!")
        print(
            f"📊 Loaded {len(documents)} documents across {len(set(doc_id_to_topic.values()))} topics"
        )
    except Exception as e:
        models_loading["status"] = False
        models_loading["progress"] = f"Error: {str(e)}"
        print(f"❌ Error loading models: {e}")
        raise


@app.on_event("startup")
async def startup_event():
    """
    Start loading models in the background.
    This function returns immediately so the server can accept connections.
    """
    import asyncio
    import concurrent.futures
    import threading

    # Start model loading in a separate thread (synchronous function)
    thread = threading.Thread(target=load_models_background, daemon=True)
    thread.start()

    # Return immediately so server can start accepting connections
    print("🚀 Server starting, models loading in background...")


@app.get("/api/status")
async def get_status():
    """
    Get the loading status of models.
    This endpoint should respond immediately even if models are still loading.
    """
    try:
        return {
            "loading": models_loading.get("status", True),
            "progress": models_loading.get("progress", "Initializing..."),
            "loaded": models_loaded,
        }
    except Exception as e:
        # Return safe defaults if there's any error
        return {"loading": True, "progress": "Initializing...", "loaded": False}


@app.get("/")
async def home(request: Request):
    """
    Serve the main page. This should respond immediately.
    """
    return templates.TemplateResponse("index.html", {"request": request})
