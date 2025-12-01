import wikipedia
import json
import time
import random
import logging
import sys
import zipfile
import shutil
from requests.exceptions import ConnectionError, Timeout
from urllib3.exceptions import SSLError
from concurrent.futures import ProcessPoolExecutor, as_completed
import os
from multiprocessing import Manager, Value, Lock as MP_Lock
import multiprocessing

# Configure logging
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")


def print_progress(message, current=0, total=0):
    """Print progress message with optional percentage."""
    if total > 0:
        percentage = (current / total) * 100
        sys.stdout.write(f"\r{message} [{current}/{total}] ({percentage:.1f}%)")
        sys.stdout.flush()
    else:
        print(message)


topics = [
    "Health",
    "Environment",
    "Technology",
    "Economy",
    "Entertainment",
    "Sports",
    "Politics",
    "Education",
    "Travel",
    "Food",
]


def retry_fetch_page(title, retries=3, delay=5):
    for attempt in range(retries):
        try:
            page = wikipedia.page(title, auto_suggest=False)
            return page
        except (wikipedia.exceptions.DisambiguationError, wikipedia.exceptions.PageError) as e:
            return None
        except (ConnectionError, Timeout, SSLError) as e:
            logging.warning(
                f"Connection error occurred: {e}. Retrying ({attempt + 1}/{retries}) in {delay} seconds..."
            )
            time.sleep(delay)
    return None


def process_topic(args):
    """
    Process a single topic and collect articles.
    Args: (topic, target_count, progress_dict, total_articles_counter, progress_lock)
    """
    topic, target_count, progress_dict, total_articles_counter, progress_lock = args

    collected_articles = []
    local_visited_titles = set()

    try:
        search_queue = wikipedia.search(topic, results=8000)
        search_queue = list(set(search_queue))  # Ensure initial uniqueness
    except Exception as e:
        logging.error(f"Error searching for topic {topic}: {e}")
        return topic, collected_articles

    article_counter = 0
    total_attempted = 0

    while len(collected_articles) < target_count and search_queue:
        current_title = search_queue.pop(0)
        total_attempted += 1

        page = retry_fetch_page(current_title)
        if not page:
            continue

        try:
            summary = page.summary
            if len(summary) < 200:
                continue

            article_data = {
                "Title": page.title,
                "URL": page.url,
                "Summary": summary,
                "Revision ID": page.revision_id,
                "Topic": topic,
            }

            collected_articles.append(article_data)
            local_visited_titles.add(page.title)
            article_counter += 1

            # Update progress
            with progress_lock:
                progress_dict[topic] = {
                    "collected": article_counter,
                    "target": target_count,
                    "attempted": total_attempted,
                }
                total_articles_counter.value += 1

            new_links = [link for link in page.links[:10] if link not in local_visited_titles]
            search_queue.extend(new_links)

            if article_counter % 100 == 0:
                save_intermediate_results(topic, collected_articles, article_counter)

            time.sleep(random.uniform(0.5, 2.0))  # Reduced delay for multiprocessing

        except wikipedia.exceptions.DisambiguationError as e:
            new_links = [option for option in e.options if option not in local_visited_titles]
            search_queue.extend(new_links)
        except (wikipedia.exceptions.PageError, ConnectionError, Timeout, SSLError) as e:
            pass  # Silently skip errors
        except Exception as e:
            logging.error(f"Unexpected error for topic {topic}: {e}")

    save_intermediate_results(topic, collected_articles, article_counter, final_save=True)

    return topic, collected_articles


def save_intermediate_results(topic, data, article_counter, final_save=False):
    os.makedirs("intermediate_p3", exist_ok=True)
    suffix = "_final" if final_save else f"_{article_counter}"
    file_path = os.path.join("intermediate_p3", f"{topic}_data{suffix}.json")
    with open(file_path, "w", encoding="utf-8") as json_file:
        json.dump(data, json_file, ensure_ascii=False, indent=4)
    logging.info(f"Saved intermediate results for topic '{topic}' to '{file_path}'")


def print_scraping_progress(
    progress_dict, total_articles, total_topics, completed_topics, progress_lock
):
    """Print current scraping progress."""
    with progress_lock:
        print("\n" + "=" * 70)
        print(
            f"📊 Scraping Progress: {completed_topics.value}/{total_topics} topics completed | Total articles: {total_articles.value}"
        )
        print("-" * 70)
        for topic in sorted(progress_dict.keys()):
            if topic in progress_dict:
                stats = progress_dict[topic]
                collected = stats.get("collected", 0)
                target = stats.get("target", 6000)
                attempted = stats.get("attempted", 0)
                pct = (collected / target * 100) if target > 0 else 0
                print(
                    f"  {topic:15s}: {collected:5d}/{target} articles ({pct:5.1f}%) | Attempted: {attempted}"
                )
        print("=" * 70 + "\n")


def extract_from_zip(zip_path, output_path):
    """
    Extract scraped_data.zip and rename the extracted file to all_topics_wikipedia_data.json
    """
    try:
        print(f"📦 Found {zip_path}, attempting to extract...")

        # Create a temporary directory for extraction
        temp_dir = "temp_extract"
        os.makedirs(temp_dir, exist_ok=True)

        with zipfile.ZipFile(zip_path, "r") as zip_ref:
            # Extract all files to temp directory
            zip_ref.extractall(temp_dir)
            print(f"✅ Extracted files from {zip_path}")

            # Find the extracted JSON file (should be only one or the main one)
            extracted_files = [f for f in os.listdir(temp_dir) if f.endswith(".json")]

            if not extracted_files:
                print(f"❌ No JSON file found in {zip_path}")
                shutil.rmtree(temp_dir, ignore_errors=True)
                return False

            # Use the first JSON file found, or look for a specific name
            extracted_file = extracted_files[0]
            if len(extracted_files) > 1:
                # Prefer files with 'all_topics' or 'wikipedia' in name
                preferred = [
                    f
                    for f in extracted_files
                    if "all_topics" in f.lower() or "wikipedia" in f.lower()
                ]
                if preferred:
                    extracted_file = preferred[0]

            source_path = os.path.join(temp_dir, extracted_file)

            # Ensure output directory exists
            os.makedirs(
                os.path.dirname(output_path) if os.path.dirname(output_path) else ".", exist_ok=True
            )

            # Copy/rename to final location
            shutil.copy2(source_path, output_path)

            import os

            file_size = os.path.getsize(output_path) / (1024 * 1024)  # Size in MB
            print(f"✅ Successfully extracted and saved to {output_path} ({file_size:.2f} MB)")

            # Clean up temp directory
            shutil.rmtree(temp_dir, ignore_errors=True)
            return True

    except zipfile.BadZipFile:
        print(f"❌ Invalid zip file: {zip_path}")
        return False
    except Exception as e:
        print(f"❌ Error extracting from zip: {e}")
        return False


def main():
    zip_path = "data/scraped_data.zip"
    output_path = "data/all_topics_wikipedia_data.json"

    # First, try to extract from zip file
    if os.path.exists(zip_path):
        print(f"📦 Checking for {zip_path}...")
        if extract_from_zip(zip_path, output_path):
            print("✅ Data extracted from zip file. Skipping internet scraping.")
            return
        else:
            print(f"⚠️  Failed to extract from {zip_path}, falling back to internet scraping...")
    else:
        print(f"📡 {zip_path} not found, proceeding with internet scraping...")

    # If zip extraction failed or zip doesn't exist, proceed with scraping
    print("\n" + "=" * 70)
    print("🚀 Starting Wikipedia Scraper (Multiprocessing)")
    print("=" * 70)

    num_topics = len(topics)
    # Get target count from environment variable, default to 600
    target_count = int(os.getenv("ARTICLES_PER_TOPIC", "600"))
    max_workers = min(multiprocessing.cpu_count(), num_topics)

    print(f"\n📊 Configuration:")
    print(f"   Topics to scrape: {num_topics}")
    print(f"   Target articles per topic: {target_count}")
    print(f"   Worker processes: {max_workers}")
    print(f"   Total target articles: {num_topics * target_count:,}")

    with Manager() as manager:
        # Shared progress tracking
        progress_dict = manager.dict()
        total_articles_counter = manager.Value("i", 0)
        completed_topics_counter = manager.Value("i", 0)
        progress_lock = manager.Lock()

        # Initialize progress for all topics
        for topic in topics:
            progress_dict[topic] = {"collected": 0, "target": target_count, "attempted": 0}

        print(f"\n🔄 Starting scraping with {max_workers} processes...\n")

        # Prepare arguments for each process
        process_args = [
            (topic, target_count, progress_dict, total_articles_counter, progress_lock)
            for topic in topics
        ]

        # Use ProcessPoolExecutor for true multiprocessing
        with ProcessPoolExecutor(max_workers=max_workers) as executor:
            # Submit all tasks
            futures = {executor.submit(process_topic, args): args[0] for args in process_args}

            # Monitor progress
            import threading

            stop_progress = threading.Event()

            def progress_monitor():
                while not stop_progress.is_set():
                    time.sleep(5)  # Update every 5 seconds
                    if not stop_progress.is_set():
                        print_scraping_progress(
                            progress_dict,
                            total_articles_counter,
                            num_topics,
                            completed_topics_counter,
                            progress_lock,
                        )

            progress_thread = threading.Thread(target=progress_monitor, daemon=True)
            progress_thread.start()

            # Process completed tasks
            for future in as_completed(futures):
                topic = futures[future]
                try:
                    result_topic, articles = future.result()
                    with progress_lock:
                        completed_topics_counter.value += 1
                        if articles:
                            print(
                                f"\n✅ Topic '{result_topic}' completed: {len(articles)} articles collected"
                            )
                        else:
                            print(f"\n⚠️  Topic '{result_topic}' completed with no articles")
                except Exception as e:
                    print(f"\n❌ Error processing topic '{topic}': {e}")

            stop_progress.set()
            progress_thread.join(timeout=1)

        # Final progress update
        print_scraping_progress(
            progress_dict,
            total_articles_counter,
            num_topics,
            completed_topics_counter,
            progress_lock,
        )

        print("\n📦 Combining intermediate results...")
        combine_intermediate_results(output_path)


def combine_intermediate_results(final_filename):
    print("📊 Combining intermediate results...")
    all_data = {}
    intermediate_dir = "intermediate_p3"

    if not os.path.exists(intermediate_dir):
        print(f"❌ Intermediate directory '{intermediate_dir}' not found!")
        return

    final_files = [f for f in os.listdir(intermediate_dir) if f.endswith("_final.json")]
    total_files = len(final_files)

    if total_files == 0:
        print(f"⚠️  No final JSON files found in '{intermediate_dir}'")
        return

    print(f"   Found {total_files} topic files to combine...")

    combined_count = 0
    for file_name in final_files:
        topic = file_name.split("_data_final.json")[0]
        file_path = os.path.join(intermediate_dir, file_name)
        try:
            with open(file_path, "r", encoding="utf-8") as json_file:
                data = json.load(json_file)
                all_data[topic] = data
                combined_count += 1
                print(f"   ✅ Combined {topic}: {len(data)} articles")
        except Exception as e:
            print(f"   ❌ Error reading {file_name}: {e}")

    print(f"\n💾 Saving combined data to {final_filename}...")
    with open(final_filename, "w", encoding="utf-8") as json_file:
        json.dump(all_data, json_file, ensure_ascii=False, indent=4)

    file_size = os.path.getsize(final_filename) / (1024 * 1024)  # Size in MB
    total_articles = sum(len(articles) for articles in all_data.values())

    print(f"\n✅ All data combined and saved!")
    print(f"   Output file: {final_filename}")
    print(f"   File size: {file_size:.2f} MB")
    print(f"   Topics: {len(all_data)}")
    print(f"   Total articles: {total_articles:,}")
    print("=" * 70)


if __name__ == "__main__":
    # Required for multiprocessing on Windows/Linux
    multiprocessing.freeze_support()
    main()
