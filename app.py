from fastapi import FastAPI, Request, HTTPException
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from pydantic import BaseModel
from transformers import BlenderbotTokenizer, BlenderbotForConditionalGeneration, T5Tokenizer, T5ForConditionalGeneration
import json

app = FastAPI()

# Load templates and static files
app.mount("/static", StaticFiles(directory="static"), name="static")
templates = Jinja2Templates(directory="templates")

# Load chat and summarization models
blenderbot_tokenizer = BlenderbotTokenizer.from_pretrained("facebook/blenderbot-400M-distill")
blenderbot_model = BlenderbotForConditionalGeneration.from_pretrained("facebook/blenderbot-400M-distill")
summary_tokenizer = T5Tokenizer.from_pretrained("t5-small")
summary_model = T5ForConditionalGeneration.from_pretrained("t5-small")

# Load documents
with open("all_topics_wikipedia_data.json") as f:
    documents = json.load(f)

# Store user-selected topic and chit-chat mode
selected_topic = {"topic": None}  # None indicates no topic selected yet
chit_chat_mode = {"active": True}  # Initially, chit-chat mode is enabled

# Define Pydantic models for request validation
class TopicRequest(BaseModel):
    topic: str

class QueryRequest(BaseModel):
    query: str

# Serve the main HTML page
@app.get("/")
async def home(request: Request):
    return templates.TemplateResponse("index.html", {"request": request})

class ChatRequest(BaseModel):
    user_message: str

@app.post("/api/chat")
async def chat(request: ChatRequest):
    # Process the user message using BlenderBot for chit-chat
    inputs = blenderbot_tokenizer(request.user_message, return_tensors="pt")
    reply_ids = blenderbot_model.generate(**inputs)
    bot_response = blenderbot_tokenizer.decode(reply_ids[0], skip_special_tokens=True)
    return {"response": bot_response}

# Endpoint to select a topic and exit chit-chat mode
@app.post("/api/select_topic")
async def select_topic(request: TopicRequest):
    selected_topic["topic"] = request.topic
    chit_chat_mode["active"] = False  # Disable chit-chat mode after selecting a topic
    return {"message": f"Topic changed to {request.topic}"}

# Retrieve and summarize endpoint, only works if chit-chat mode is off and topic is selected
@app.post("/api/retrieve_and_summarize")
async def retrieve_and_summarize(request: QueryRequest):
    if chit_chat_mode["active"]:
        raise HTTPException(status_code=400, detail="Please select a topic before querying.")

    topic = selected_topic["topic"]
    if not topic:
        raise HTTPException(status_code=400, detail="No topic selected.")

    top_docs = documents.get(topic, [])[:3]  # Retrieve top 3 docs for the selected topic

    # Combine query with document content and generate summary
    combined_text = request.query + " " + " ".join(top_docs)
    inputs = summary_tokenizer("summarize: " + combined_text, return_tensors="pt", max_length=512, truncation=True)
    summary_ids = summary_model.generate(inputs["input_ids"], max_length=150, min_length=40, length_penalty=2.0, num_beams=4, early_stopping=True)
    summary = summary_tokenizer.decode(summary_ids[0], skip_special_tokens=True)

    return {"summary": summary}

# Dummy endpoint for visualization data
@app.get("/api/get_visualization_data")
async def get_visualization_data():
    # Example data for visualization, replace with actual analytics
    return {
        "topic_usage": {"Technology": 15, "Health": 10, "Environment": 8},
        "message_lengths": [5, 10, 15, 20],
        "response_times": [1.2, 1.5, 1.8, 2.0]
    }


class ChatRequest(BaseModel):
    user_message: str

@app.post("/api/chat")
async def chat(request: ChatRequest):
    # If in chit-chat mode, respond using BlenderBot
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
    # Here, you could process the topic selection, e.g., set a global state or start a new conversation
    print(f"Topic selected: {request.topic}")
    return {"message": f"Topic '{request.topic}' selected"}