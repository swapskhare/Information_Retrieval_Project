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
# Preload nltk stopwords
nltk.download('stopwords')
stop_words = set(nltk.corpus.stopwords.words('english'))

# Initialize FastAPI
app = FastAPI()

# Load templates and static files
app.mount("/static", StaticFiles(directory="static"), name="static")
templates = Jinja2Templates(directory="templates")

# Chat and summarization models
blenderbot_tokenizer = BlenderbotTokenizer.from_pretrained("facebook/blenderbot-400M-distill")
blenderbot_model = BlenderbotForConditionalGeneration.from_pretrained("facebook/blenderbot-400M-distill")
summarizer = pipeline("summarization", model="facebook/bart-large-cnn", device=-1)  # Use GPU (device=0) or CPU (device=-1)

# Load postings list
with open("data/postings_list.json", "r") as f:
    postings_list = json.load(f)

# Load documents
with open("data/all_topics_wikipedia_data.json", "r") as f:
    documents = json.load(f)

with open("data/doc_id_to_url.json", "r") as f:
    doc_id_to_url = json.load(f)

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
def fetch_url_content(url):
    try:
        response = requests.get(url)
        response.raise_for_status()
        soup = BeautifulSoup(response.text, "html.parser")
        paragraphs = soup.find_all("p")
        content = " ".join([para.get_text() for para in paragraphs])
        return content.strip()
    except requests.exceptions.RequestException as e:
        print(f"Error fetching the URL: {e}")
        return ""

# Split text into chunks
def chunk_text(text, max_tokens=500):
    words = text.split()
    for i in range(0, len(words), max_tokens):
        yield " ".join(words[i:i + max_tokens])

# Generate a dynamic summary
def generate_dynamic_summary(content, query):
    input_text = f"Query: {query}\n\nContent: {content}"
    chunks = list(chunk_text(input_text, max_tokens=500))
    summaries = []
    for chunk in chunks:
        try:
            summary = summarizer(chunk, max_length=150, min_length=40, do_sample=False)
            summaries.append(summary[0]["summary_text"])
        except Exception as e:
            print(f"Error generating summary for chunk: {e}")
            continue
    return " ".join(summaries)

class ChatRequest(BaseModel):
    user_message: str

@app.post("/api/chat")
async def chat(request: ChatRequest):
    # If chit-chat mode is active, respond using BlenderBot
    if chit_chat_mode["active"]:
        inputs = blenderbot_tokenizer(request.user_message, return_tensors="pt")
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
    if chit_chat_mode["active"]:
        raise HTTPException(status_code=400, detail="Please select a topic before querying.")

    topic = selected_topic["topic"]
    if not topic:
        raise HTTPException(status_code=400, detail="No topic selected.")

    # Retrieve relevant documents
    query = request.query
    start_time = time.time()
    relevant_doc_ids = retrieve_top_docs(query, postings_list)

    # Filter documents by topic
    topic_filtered_ids = []
    for doc_id in relevant_doc_ids:
        for term, postings in postings_list.items():
            for posting in postings:
                if posting["doc_id"] == doc_id and posting["topic"] == topic:
                    topic_filtered_ids.append(doc_id)
                    break

    if not topic_filtered_ids:
        end_time = time.time()  # Measure end time for no summaries
        response_time = (end_time - start_time) * 1000  # Calculate response time in milliseconds
        result = {"summary": f"No relevant documents found for the query that match the selected topic '{topic}'."}
        # save_query_to_json(query, result["summary"], topic)  # Save the result
        save_query_to_json(query, result["summary"], response_time, topic)  # Save the result

        return result

    # Generate summaries for relevant documents
    processed_doc_ids = set()
    top_summaries = []

    for doc_id in set(topic_filtered_ids):
        if doc_id in processed_doc_ids:
            continue
        processed_doc_ids.add(doc_id)

        url = doc_id_to_url.get(str(doc_id), None)
        if url:
            url_content = fetch_url_content(url)
            if url_content:
                dynamic_summary = generate_dynamic_summary(url_content, query)
                top_summaries.append(dynamic_summary)

    if not top_summaries:
        end_time = time.time()  # Measure end time for no summaries
        response_time = (end_time - start_time) * 1000  # Calculate response time in milliseconds
        result = {"summary": "No relevant content found for the query."}
        save_query_to_json(query, result["summary"], topic)  # Save the result
        return result

    # Measure response time

    end_time = time.time()
    response_time = (end_time - start_time) * 1000

    summary = " ".join(top_summaries)
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
    data[query] = {
        "result": result,
        "response_time": response_time,
        "topic": topic
    }

    with open(file_path, "w") as file:
        json.dump(data, file, indent=4)


@app.get("/")
async def home(request: Request):
    return templates.TemplateResponse("index.html", {"request": request})