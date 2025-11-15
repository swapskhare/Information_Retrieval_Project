import json
import sys


def print_progress(message, current=0, total=0):
    """Print progress message with optional percentage."""
    if total > 0:
        percentage = (current / total) * 100
        sys.stdout.write(f"\r{message} [{current}/{total}] ({percentage:.1f}%)")
        sys.stdout.flush()
    else:
        print(message)


print("📥 Loading documents...")
# Load documents
with open("data/all_topics_wikipedia_data.json", "r") as f:
    documents = json.load(f)

print(f"✅ Loaded documents with {len(documents)} topics")

print("\n🔗 Creating doc_id to URL mapping...")
# Create a mapping from sequential doc_id to URL (matching indexer.py)
doc_id_to_url = {}
doc_id = 0
total_docs = sum(len(records) for records in documents.values())

for topic, records in documents.items():
    for doc in records:
        url = doc.get("URL", "")
        if url:  # Only add if URL exists
            doc_id_to_url[doc_id] = url
        doc_id += 1
        if doc_id % 10000 == 0 or doc_id == total_docs:
            print_progress("  Mapping documents", doc_id, total_docs)

print(f"\n✅ Created mapping for {len(doc_id_to_url)} documents")

# Save the mapping to a file
print("\n💾 Saving mapping to file...")
with open("data/doc_id_to_url.json", "w") as f:
    json.dump(doc_id_to_url, f, indent=2)

print(f"✅ doc_id_to_url mapping saved to data/doc_id_to_url.json")
print(f"   Total mappings: {len(doc_id_to_url)}")
