import json

# Load documents
with open("all_topics_wikipedia_data.json", "r") as f:
    documents = json.load(f)

# Create a mapping from doc_id to URL
doc_id_to_url = {}
for topic_docs in documents.values():
    for doc in topic_docs:
        doc_id = int(doc.get("Revision ID", -1))  # Use Revision ID as doc_id
        if doc_id != -1:
            doc_id_to_url[doc_id] = doc.get("URL", "")

# Save the mapping to a file
with open("doc_id_to_url.json", "w") as f:
    json.dump(doc_id_to_url, f)
print("doc_id_to_url mapping saved!")