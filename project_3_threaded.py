import wikipedia
import json
import pandas as pd
import time
import random
import logging
import threading
from requests.exceptions import ConnectionError, Timeout
from urllib3.exceptions import SSLError
from concurrent.futures import ThreadPoolExecutor, as_completed
import os
from multiprocessing import Manager

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

topics = [
    "Health", "Environment", "Technology", "Economy",
    "Entertainment", "Sports", "Politics", "Education",
    "Travel", "Food"
]

def retry_fetch_page(title, retries=3, delay=5):
    for attempt in range(retries):
        try:
            page = wikipedia.page(title, auto_suggest=False)
            return page
        except (wikipedia.exceptions.DisambiguationError, wikipedia.exceptions.PageError) as e:
            return None
        except (ConnectionError, Timeout, SSLError) as e:
            logging.warning(f"Connection error occurred: {e}. Retrying ({attempt + 1}/{retries}) in {delay} seconds...")
            time.sleep(delay)
    return None

def process_topic(topic, target_count, visited_pages, lock):
    logging.info(f"Starting to fetch data for topic: {topic}")
    
    collected_articles = []
    local_visited_titles = set()
    search_queue = wikipedia.search(topic, results=8000)
    search_queue = list(set(search_queue))  # Ensure initial uniqueness
    article_counter = 0
    
    while len(collected_articles) < target_count and search_queue:
        current_title = search_queue.pop(0)
        
        with lock:
            if current_title in visited_pages:
                continue

        page = retry_fetch_page(current_title)
        if not page:
            continue
        
        try:
            summary = page.summary
            if len(summary) < 200:
                continue
            
            article_data = {
                'Title': page.title,
                'URL': page.url,
                'Summary': summary,
                'Revision ID': page.revision_id,
                'Topic': topic
            }
            
            collected_articles.append(article_data)
            local_visited_titles.add(page.title)
            article_counter += 1
            
            with lock:
                visited_pages[page.title] = True
            
            new_links = [link for link in page.links[:10] if link not in visited_pages]
            search_queue.extend(new_links)
            
            logging.info(f"Successfully fetched article: {page.title} for topic: {topic}")
            
            if article_counter % 100 == 0:
                save_intermediate_results(topic, collected_articles, article_counter)
                logging.info(f"Intermediate progress saved for topic '{topic}' after {article_counter} articles")
            
            time.sleep(random.uniform(1, 3))
        
        except wikipedia.exceptions.DisambiguationError as e:
            new_links = [option for option in e.options if option not in visited_pages]
            search_queue.extend(new_links)
        except (wikipedia.exceptions.PageError, ConnectionError, Timeout, SSLError) as e:
            logging.error(f"An error occurred: {e}")
        except Exception as e:
            logging.error(f"Unexpected error occurred: {e}")
    
    save_intermediate_results(topic, collected_articles, article_counter, final_save=True)

    if len(collected_articles) < 6000:
        logging.warning(f"Insufficient articles with long summaries for topic {topic}. Collected only {len(collected_articles)}.")
        return None

    return collected_articles

def save_intermediate_results(topic, data, article_counter, final_save=False):
    os.makedirs('intermediate_p3', exist_ok=True)
    suffix = "_final" if final_save else f"_{article_counter}"
    file_path = os.path.join('intermediate_p3', f"{topic}_data{suffix}.json")
    with open(file_path, "w", encoding="utf-8") as json_file:
        json.dump(data, json_file, ensure_ascii=False, indent=4)
    logging.info(f"Saved intermediate results for topic '{topic}' to '{file_path}'")

def thread_safe_collect(topic, target_count, visited_pages, lock):
    process_topic(topic, target_count, visited_pages, lock)

def main():
    with Manager() as manager:
        visited_pages = manager.dict()
        lock = manager.Lock()

        max_workers = 10
        logging.info(f"Using {max_workers} worker threads based on CPU count.")

        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            futures = [
                executor.submit(thread_safe_collect, topic, 6000, visited_pages, lock) for topic in topics
            ]
            
            for future in as_completed(futures):
                try:
                    future.result()
                except Exception as e:
                    logging.error(f"An error occurred: {e}")

        combine_intermediate_results("all_data_wikipedia.json")

def combine_intermediate_results(final_filename):
    all_data = {}
    intermediate_dir = 'intermediate_p3'
    
    for file_name in os.listdir(intermediate_dir):
        if file_name.endswith("_final.json"):
            topic = file_name.split("_data_final.json")[0]
            with open(os.path.join(intermediate_dir, file_name), "r", encoding="utf-8") as json_file:
                data = json.load(json_file)
                all_data[topic] = data

    with open(final_filename, "w", encoding="utf-8") as json_file:
        json.dump(all_data, json_file, ensure_ascii=False, indent=4)

    logging.info(f"All data combined and saved to '{final_filename}'")

if __name__ == "__main__":
    main()
