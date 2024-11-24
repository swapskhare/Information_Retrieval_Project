import re
import json
import math
from nltk.stem import PorterStemmer
from collections import defaultdict
import nltk

# Download stopwords if not already present
nltk.download('stopwords')
stop_words = set(nltk.corpus.stopwords.words('english'))

# Preprocessing Function
ps = PorterStemmer()

def preprocess_text(text):
    """
    Preprocess text by lowercasing, removing special characters, tokenizing, removing stopwords, and stemming.
    """
    text = text.lower()  # Convert to lowercase
    text = re.sub(r'[^a-z0-9\s]', ' ', text)  # Remove special characters
    text = re.sub(r'\s+', ' ', text).strip()  # Remove extra spaces
    tokens = text.split()  # Tokenize
    tokens = [ps.stem(word) for word in tokens if word not in stop_words]  # Stemming & remove stopwords
    return tokens

# Load and Prepare Data

file_path = './all_topics_wikipedia_data_p3.json'

with open(file_path, 'r', encoding='utf-8') as file:
    data = json.load(file)

documents = []
doc_id = 0

for topic, records in data.items():
    for record in records:
        documents.append({
            "id": doc_id,
            "title": record["Title"],
            "summary": record["Summary"],
            "url": record["URL"],
            "topic": topic
        })
        doc_id += 1

# Tokenize Documents
document_tokenized = {}
for doc in documents:
    tokens = preprocess_text(doc["title"] + " " + doc["summary"])  # Use title and summary
    document_tokenized[doc["id"]] = tokens

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
def create_postings_list(documents):
    postings = defaultdict(PostingsList)
    total_docs = len(documents)

    for doc_id, tokens in documents.items():
        token_count = defaultdict(int)

        for token in tokens:
            token_count[token] += 1

        total_tokens = len(tokens)

        for token, count in token_count.items():
            tf = count / total_tokens
            idf = math.log(total_docs / postings[token].size) if postings[token].head else math.log(total_docs)
            tf_idf = tf * idf
            postings[token].add_node(doc_id, tf_idf)

    for token, plist in postings.items():
        plist.add_skips()

    return postings

postings_list = create_postings_list(document_tokenized)

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

    return {"num_comparisons": comparisons, "num_docs": len(result_docs), "results": sorted(result_docs)}

# Example Query
query = "engineering manufacturing process"
result = daat_and_query_with_skips(postings_list, query)

print("DAAT AND Query with Skips Results:", result)
