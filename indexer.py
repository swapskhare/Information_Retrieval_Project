import re
import json
import math
import sys
from nltk.stem import PorterStemmer
from collections import defaultdict
import nltk

# Download stopwords if not already present
nltk.download("stopwords", quiet=True)
stop_words = set(nltk.corpus.stopwords.words("english"))


def print_progress(message, current=0, total=0):
    """Print progress message with optional percentage."""
    if total > 0:
        percentage = (current / total) * 100
        sys.stdout.write(f"\r{message} [{current}/{total}] ({percentage:.1f}%)")
        sys.stdout.flush()
    else:
        print(message)


# Preprocessing Function
ps = PorterStemmer()


def preprocess_text(text):
    """
    Preprocess text by lowercasing, removing special characters, tokenizing, removing stopwords, and stemming.
    """
    text = text.lower()  # Convert to lowercase
    text = re.sub(r"[^a-z0-9\s]", " ", text)  # Remove special characters
    text = re.sub(r"\s+", " ", text).strip()  # Remove extra spaces
    tokens = text.split()  # Tokenize
    tokens = [
        ps.stem(word) for word in tokens if word not in stop_words
    ]  # Stemming & remove stopwords
    return tokens


# Load and Prepare Data
print("📥 Loading data file...")
file_path = "./data/all_topics_wikipedia_data.json"

with open(file_path, "r", encoding="utf-8") as file:
    data = json.load(file)

print(f"✅ Loaded data file with {len(data)} topics")

print("\n📝 Preparing documents...")
documents = []
doc_id = 0
total_records = sum(len(records) for records in data.values())
current_record = 0

for topic, records in data.items():
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
        doc_id += 1
        current_record += 1
        if current_record % 1000 == 0 or current_record == total_records:
            print_progress("  Preparing documents", current_record, total_records)

print(f"\n✅ Prepared {len(documents)} documents")

# Tokenize Documents
print("\n🔤 Tokenizing documents...")
document_tokenized = {}
total_docs = len(documents)
for idx, doc in enumerate(documents):
    tokens = preprocess_text(doc["title"] + " " + doc["summary"])  # Use title and summary
    document_tokenized[doc["id"]] = tokens
    if (idx + 1) % 1000 == 0 or (idx + 1) == total_docs:
        print_progress("  Tokenizing", idx + 1, total_docs)

print(f"\n✅ Tokenized {len(document_tokenized)} documents")


# Postings List Classes
class PostingsNode:
    def __init__(self, doc_id, tf_idf):
        self.doc_id = doc_id
        self.next = None
        self.skip = None
        self.tf_idf = tf_idf


class PostingsList:
    def __init__(self):
        self.head = None
        self.size = 0

    def add_node(self, doc_id, tf_idf):
        """
        Add a new node to the postings list.
        """
        node = PostingsNode(doc_id, tf_idf)
        if not self.head or self.head.doc_id > doc_id:
            node.next = self.head
            self.head = node
        else:
            prev = None
            curr = self.head
            while curr and curr.doc_id < doc_id:
                prev = curr
                curr = curr.next
            node.next = curr
            if prev:
                prev.next = node
        self.size += 1

    def add_skips(self):
        """
        Add skip pointers to optimize query processing.
        """
        skip_interval = round(math.sqrt(self.size))
        if skip_interval <= 1:
            return
        curr = self.head
        prev_skip = None
        index = 0
        while curr:
            if index % skip_interval == 0:
                if prev_skip:
                    prev_skip.skip = curr
                prev_skip = curr
            index += 1
            curr = curr.next


# Create Postings List
def create_postings_list(documents, show_progress=True):
    postings = defaultdict(PostingsList)
    total_docs = len(documents)

    if show_progress:
        print("\n📊 Creating inverted index with TF-IDF scores...")

    processed = 0
    for doc_id, tokens in documents.items():
        token_count = defaultdict(int)

        for token in tokens:
            token_count[token] += 1

        total_tokens = len(tokens)

        for token, count in token_count.items():
            tf = count / total_tokens
            idf = (
                math.log(total_docs / postings[token].size)
                if postings[token].head
                else math.log(total_docs)
            )
            tf_idf = tf * idf
            postings[token].add_node(doc_id, tf_idf)

        processed += 1
        if show_progress and (processed % 1000 == 0 or processed == total_docs):
            print_progress("  Processing documents", processed, total_docs)

    if show_progress:
        print(f"\n✅ Processed {processed} documents")
        print(f"\n🔗 Adding skip pointers...")

    total_terms = len(postings)
    skip_processed = 0
    for token, plist in postings.items():
        plist.add_skips()
        skip_processed += 1
        if show_progress and (skip_processed % 10000 == 0 or skip_processed == total_terms):
            print_progress("  Adding skip pointers", skip_processed, total_terms)

    if show_progress:
        print(f"\n✅ Added skip pointers to {total_terms} terms")

    return postings


print("\n🔨 Building inverted index...")
postings_list = create_postings_list(document_tokenized)


# Convert postings list to JSON-serializable format
def postings_to_dict(postings_list, show_progress=True):
    """
    Convert PostingsList objects to JSON-serializable dictionary format.
    """
    if show_progress:
        print("\n🔄 Converting postings list to JSON format...")

    result = {}
    total_terms = len(postings_list)
    processed = 0

    for term, plist in postings_list.items():
        postings = []
        curr = plist.head
        while curr:
            postings.append(
                {
                    "doc_id": curr.doc_id,
                    "tf_idf": curr.tf_idf,
                    "topic": None,  # Will be filled from documents if needed
                }
            )
            curr = curr.next
        result[term] = postings
        processed += 1
        if show_progress and (processed % 10000 == 0 or processed == total_terms):
            print_progress("  Converting terms", processed, total_terms)

    if show_progress:
        print(f"\n✅ Converted {processed} terms")

    return result


postings_dict = postings_to_dict(postings_list)

# Add topic information to postings
print("\n🏷️  Adding topic information to postings...")
total_postings = sum(len(postings) for postings in postings_dict.values())
processed_postings = 0

for term, postings in postings_dict.items():
    for posting in postings:
        doc_id = posting["doc_id"]
        if doc_id < len(documents):
            posting["topic"] = documents[doc_id]["topic"]
        processed_postings += 1
        if processed_postings % 100000 == 0 or processed_postings == total_postings:
            print_progress("  Adding topics", processed_postings, total_postings)

print(f"\n✅ Added topic information to {processed_postings} postings")

# Save postings list to JSON
print("\n💾 Saving postings list to JSON file...")
output_file = "./data/postings_list.json"
with open(output_file, "w", encoding="utf-8") as f:
    json.dump(postings_dict, f, indent=2, ensure_ascii=False)

import os

file_size = os.path.getsize(output_file) / (1024 * 1024)  # Size in MB
print(f"✅ Postings list saved to {output_file} ({file_size:.2f} MB)")


# DAAT AND Query with Skips
def daat_and_query_with_skips(postings_list, query_terms):
    """
    Perform a DAAT AND query using skip pointers.
    """
    query_terms = preprocess_text(query_terms)  # Preprocess query
    if not query_terms:
        return {"num_comparisons": 0, "num_docs": 0, "results": []}

    postings = [postings_list[term] for term in query_terms if term in postings_list]
    if not postings:
        return {"num_comparisons": 0, "num_docs": 0, "results": []}

    pointers = [plist.head for plist in postings]
    result_docs = []
    comparisons = 0

    while all(pointers):
        max_doc_id = max(p.doc_id for p in pointers if p)
        matches = [p for p in pointers if p.doc_id == max_doc_id]

        if len(matches) == len(pointers):
            result_docs.append(max_doc_id)
            pointers = [p.next for p in pointers]
            comparisons += 1
        else:
            for i, p in enumerate(pointers):
                while p and p.doc_id < max_doc_id:
                    comparisons += 1
                    if p.skip and p.skip.doc_id <= max_doc_id:
                        p = p.skip
                    else:
                        p = p.next
                pointers[i] = p

    return {
        "num_comparisons": comparisons,
        "num_docs": len(result_docs),
        "results": sorted(result_docs),
    }


# Example Query
print("\n🧪 Testing query processing...")
query = "engineering manufacturing process"
result = daat_and_query_with_skips(postings_list, query)

print(f"\n✅ Query test completed:")
print(f"   Query: '{query}'")
print(f"   Documents found: {result['num_docs']}")
print(f"   Comparisons: {result['num_comparisons']}")
print(f"   Results: {result['results'][:5]}{'...' if len(result['results']) > 5 else ''}")

print("\n" + "=" * 60)
print("✅ Indexing complete!")
print(f"   Total documents: {len(documents)}")
print(f"   Total terms: {len(postings_list)}")
print(f"   Output file: {output_file}")
print("=" * 60)
