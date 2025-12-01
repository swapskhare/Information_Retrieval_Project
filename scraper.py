import json
import asyncio
import aiohttp
import logging
import sys
import zipfile
import shutil
import os
import random
from typing import Dict, List, Optional, Tuple
from urllib.parse import quote
from asyncio import Lock as AsyncLock

# Configure logging
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")

# Wikipedia API base URL
WIKIPEDIA_API_URL = "https://en.wikipedia.org/w/api.php"
USER_AGENT = "WikipediaScraper/1.0 (https://github.com/user/project; contact@example.com)"


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


async def fetch_wikipedia_search(session: aiohttp.ClientSession, query: str, limit: int = 8000) -> List[str]:
    """Search Wikipedia for articles matching the query."""
    titles = []
    continue_token = None
    
    try:
        while len(titles) < limit:
            params = {
                "action": "query",
                "list": "search",
                "srsearch": query,
                "srlimit": min(500, limit - len(titles)),  # API limit is 500 per request
                "format": "json",
            }
            
            if continue_token:
                params["srcontinue"] = continue_token
            
            async with session.get(WIKIPEDIA_API_URL, params=params) as response:
                if response.status != 200:
                    logging.warning(f"Search API returned status {response.status}")
                    break
                
                data = await response.json()
                if "query" not in data or "search" not in data["query"]:
                    break
                
                search_results = data["query"]["search"]
                batch_titles = [result["title"] for result in search_results]
                titles.extend(batch_titles)
                
                # Check if there are more results
                if "continue" in data and "srcontinue" in data["continue"]:
                    continue_token = data["continue"]["srcontinue"]
                else:
                    break
        
        return list(set(titles))  # Remove duplicates
    
    except Exception as e:
        logging.error(f"Error searching Wikipedia for '{query}': {e}")
        return []


async def fetch_wikipedia_page(session: aiohttp.ClientSession, title: str, semaphore: asyncio.Semaphore) -> Optional[Dict]:
    """Fetch a Wikipedia page with extract, URL, and revision ID."""
    async with semaphore:  # Rate limiting
        try:
            # URL encode the title
            encoded_title = quote(title.replace(" ", "_"))
            
            params = {
                "action": "query",
                "prop": "extracts|info",
                "titles": title,
                "exintro": True,  # Get only intro section
                "explaintext": True,  # Plain text, no HTML
                "inprop": "url|revision",
                "format": "json",
            }
            
            async with session.get(WIKIPEDIA_API_URL, params=params) as response:
                if response.status != 200:
                    return None
                
                data = await response.json()
                
                if "query" not in data or "pages" not in data["query"]:
                    return None
                
                pages = data["query"]["pages"]
                page_id = list(pages.keys())[0]
                
                if page_id == "-1":  # Page doesn't exist
                    return None
                
                page_data = pages[page_id]
                
                # Check for disambiguation or redirect
                if "missing" in page_data or "invalid" in page_data:
                    return None
                
                extract = page_data.get("extract", "")
                if not extract or len(extract) < 200:
                    return None
                
                # Get URL and revision ID
                canonical_url = page_data.get("canonicalurl", "")
                revision_id = None
                if "revisions" in page_data and page_data["revisions"]:
                    revision_id = page_data["revisions"][0].get("revid")
                
                return {
                    "title": page_data.get("title", title),
                    "url": canonical_url,
                    "summary": extract[:5000],  # Limit summary length
                    "revision_id": revision_id,
                }
        
        except asyncio.TimeoutError:
            logging.warning(f"Timeout fetching page: {title}")
            return None
        except Exception as e:
            logging.debug(f"Error fetching page '{title}': {e}")
            return None


async def fetch_wikipedia_links(session: aiohttp.ClientSession, title: str, limit: int = 10) -> List[str]:
    """Fetch links from a Wikipedia page."""
    try:
        params = {
            "action": "query",
            "prop": "links",
            "titles": title,
            "pllimit": limit,
            "format": "json",
        }
        
        async with session.get(WIKIPEDIA_API_URL, params=params) as response:
            if response.status != 200:
                return []
            
            data = await response.json()
            
            if "query" not in data or "pages" not in data["query"]:
                return []
            
            pages = data["query"]["pages"]
            page_id = list(pages.keys())[0]
            
            if page_id == "-1" or "links" not in pages[page_id]:
                return []
            
            links = pages[page_id]["links"]
            return [link["title"] for link in links[:limit]]
    
    except Exception as e:
        logging.debug(f"Error fetching links for '{title}': {e}")
        return []


async def process_topic(
    session: aiohttp.ClientSession,
    topic: str,
    target_count: int,
    progress_dict: Dict,
    total_articles_counter: List[int],
    completed_topics_counter: List[int],
    progress_lock: AsyncLock,
    semaphore: asyncio.Semaphore,
):
    """Process a single topic and collect articles asynchronously."""
    collected_articles = []
    local_visited_titles = set()
    
    try:
        # Search for articles
        search_results = await fetch_wikipedia_search(session, topic, limit=8000)
        search_queue = list(set(search_results))  # Ensure uniqueness
        
        if not search_queue:
            logging.error(f"No search results for topic: {topic}")
            return topic, collected_articles
    
    except Exception as e:
        logging.error(f"Error searching for topic {topic}: {e}")
        return topic, collected_articles
    
    article_counter = 0
    total_attempted = 0
    
    # Process articles with concurrency
    pending_tasks = []
    
    while len(collected_articles) < target_count and (search_queue or pending_tasks):
        # Start new fetch tasks if we have room and queue items
        while len(pending_tasks) < 50 and search_queue and len(collected_articles) < target_count:
            current_title = search_queue.pop(0)
            if current_title not in local_visited_titles:
                task = asyncio.create_task(fetch_wikipedia_page(session, current_title, semaphore))
                pending_tasks.append((task, current_title))
                total_attempted += 1
        
        if not pending_tasks:
            break
        
        # Wait for at least one task to complete
        done, _ = await asyncio.wait(
            [task for task, _ in pending_tasks], return_when=asyncio.FIRST_COMPLETED
        )
        
        # Process completed tasks
        new_pending = []
        for task, title in pending_tasks:
            if task in done:
                page_data = await task
                if page_data:
                    summary = page_data.get("summary", "")
                    if len(summary) >= 200:
                        article_data = {
                            "Title": page_data["title"],
                            "URL": page_data.get("url", ""),
                            "Summary": summary,
                            "Revision ID": page_data.get("revision_id"),
                            "Topic": topic,
                        }
                        
                        collected_articles.append(article_data)
                        local_visited_titles.add(page_data["title"])
                        article_counter += 1
                        
                        # Update progress
                        async with progress_lock:
                            progress_dict[topic] = {
                                "collected": article_counter,
                                "target": target_count,
                                "attempted": total_attempted,
                            }
                            total_articles_counter[0] += 1
                        
                        # Fetch links for next batch
                        if len(collected_articles) < target_count:
                            links = await fetch_wikipedia_links(session, page_data["title"], limit=10)
                            for link in links:
                                if link not in local_visited_titles and link not in search_queue:
                                    search_queue.append(link)
                        
                        # Save intermediate results
                        if article_counter % 100 == 0:
                            await asyncio.to_thread(
                                save_intermediate_results, topic, collected_articles, article_counter
                            )
                else:
                    # Try to get links even if page wasn't valid (for disambiguation)
                    if len(collected_articles) < target_count:
                        links = await fetch_wikipedia_links(session, title, limit=10)
                        for link in links:
                            if link not in local_visited_titles and link not in search_queue:
                                search_queue.append(link)
            else:
                new_pending.append((task, title))
        
        pending_tasks = new_pending
        
        # Small delay to avoid hammering the API
        await asyncio.sleep(random.uniform(0.1, 0.3))
    
    # Cancel any remaining pending tasks
    for task, _ in pending_tasks:
        task.cancel()
    
    # Save final results
    await asyncio.to_thread(save_intermediate_results, topic, collected_articles, article_counter, final_save=True)
    
    async with progress_lock:
        completed_topics_counter[0] += 1
    
    return topic, collected_articles


def save_intermediate_results(topic, data, article_counter, final_save=False):
    os.makedirs("intermediate_p3", exist_ok=True)
    suffix = "_final" if final_save else f"_{article_counter}"
    file_path = os.path.join("intermediate_p3", f"{topic}_data{suffix}.json")
    with open(file_path, "w", encoding="utf-8") as json_file:
        json.dump(data, json_file, ensure_ascii=False, indent=4)
    logging.info(f"Saved intermediate results for topic '{topic}' to '{file_path}'")


async def print_scraping_progress(
    progress_dict: Dict,
    total_articles: List[int],
    total_topics: int,
    completed_topics: List[int],
    progress_lock: AsyncLock,
):
    """Print current scraping progress."""
    async with progress_lock:
        print("\n" + "=" * 70)
        print(
            f"📊 Scraping Progress: {completed_topics[0]}/{total_topics} topics completed | Total articles: {total_articles[0]}"
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


async def main_async():
    zip_path = "data/scraped_data.zip"
    output_path = "data/all_topics_wikipedia_data.json"
    
    # Skip zip extraction in CodeBuild - only extract locally
    is_codebuild = os.getenv("CODEBUILD_BUILD_ID") is not None
    
    # Only try to extract from zip file when running locally (not in CodeBuild)
    if not is_codebuild:
        if os.path.exists(zip_path):
            print(f"📦 Checking for {zip_path}...")
            if extract_from_zip(zip_path, output_path):
                print("✅ Data extracted from zip file. Skipping internet scraping.")
                return
            else:
                print(f"⚠️  Failed to extract from {zip_path}, falling back to internet scraping...")
        else:
            print(f"📡 {zip_path} not found, proceeding with internet scraping...")
    else:
        print("🔨 Running in CodeBuild - skipping zip extraction, proceeding with internet scraping...")
    
    # If zip extraction failed or zip doesn't exist, proceed with scraping
    print("\n" + "=" * 70)
    print("🚀 Starting Wikipedia Scraper (Async)")
    print("=" * 70)
    
    num_topics = len(topics)
    # Get target count from environment variable, default to 600
    target_count = int(os.getenv("ARTICLES_PER_TOPIC", "600"))
    # Get max concurrent requests from env or default to 100
    max_concurrent = int(os.getenv("MAX_CONCURRENT", "100"))
    
    print(f"\n📊 Configuration:")
    print(f"   Topics to scrape: {num_topics}")
    print(f"   Target articles per topic: {target_count}")
    print(f"   Max concurrent requests: {max_concurrent}")
    print(f"   Total target articles: {num_topics * target_count:,}")
    
    # Shared progress tracking (async-safe structures)
    progress_dict = {}
    total_articles_counter = [0]
    completed_topics_counter = [0]
    progress_lock = AsyncLock()
    
    # Semaphore for rate limiting
    semaphore = asyncio.Semaphore(max_concurrent)
    
    # Initialize progress for all topics
    for topic in topics:
        progress_dict[topic] = {"collected": 0, "target": target_count, "attempted": 0}
    
    print(f"\n🔄 Starting async scraping...\n")
    
    # Create aiohttp session
    timeout = aiohttp.ClientTimeout(total=30, connect=10)
    connector = aiohttp.TCPConnector(limit=max_concurrent * 2, limit_per_host=max_concurrent)
    
    async with aiohttp.ClientSession(
        timeout=timeout,
        connector=connector,
        headers={"User-Agent": USER_AGENT}
    ) as session:
        # Progress monitor task
        stop_progress = asyncio.Event()
        
        async def progress_monitor():
            while not stop_progress.is_set():
                await asyncio.sleep(5)  # Update every 5 seconds
                if not stop_progress.is_set():
                    await print_scraping_progress(
                        progress_dict,
                        total_articles_counter,
                        num_topics,
                        completed_topics_counter,
                        progress_lock,
                    )
        
        monitor_task = asyncio.create_task(progress_monitor())
        
        # Process all topics concurrently
        tasks = [
            process_topic(
                session,
                topic,
                target_count,
                progress_dict,
                total_articles_counter,
                completed_topics_counter,
                progress_lock,
                semaphore,
            )
            for topic in topics
        ]
        
        # Wait for all topics to complete
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # Stop progress monitor
        stop_progress.set()
        monitor_task.cancel()
        try:
            await monitor_task
        except asyncio.CancelledError:
            pass
        
        # Print completion messages
        for result in results:
            if isinstance(result, Exception):
                logging.error(f"Error processing topic: {result}")
            elif isinstance(result, tuple):
                topic, articles = result
                if articles:
                    print(f"\n✅ Topic '{topic}' completed: {len(articles)} articles collected")
                else:
                    print(f"\n⚠️  Topic '{topic}' completed with no articles")
    
    # Final progress update
    await print_scraping_progress(
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


def main():
    """Main entry point - runs the async main function."""
    asyncio.run(main_async())


if __name__ == "__main__":
    main()
