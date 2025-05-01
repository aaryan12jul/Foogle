from bs4 import BeautifulSoup
import requests
import time
import random
from queue import Queue
from concurrent.futures import ThreadPoolExecutor
import threading
from indexer import index_page

def crawl(args):
    # Unpack arguments
    queue = args['queue']
    visited_urls = args['visited_urls']
    crawl_count = args['crawl_count']
    CRAWL_LIMIT = args['CRAWL_LIMIT']
    lock = args['lock']
    stop_crawl = args['stop_crawl']
    indexed_pages = args['indexed_pages']

    # Stop Event to Manually Stop Crawling
    while not stop_crawl.is_set():
        # Getting URL to crawl from queue
        try:
            current_url = queue.get(timeout=5)
            print("Time to crawl: " + current_url)
        except Exception:
            break  # Break if queue is empty
        
        # Adding URL to Visited Set | Lock is Used to Prevent Multiple Threads from Modifying the Same Data
        with lock:
            if crawl_count[0] >= CRAWL_LIMIT:
                queue.queue.clear()  # Clear remaining URLs to stop processing
                print("Crawl limit reached. Exiting...")
                stop_crawl.set()
                break
            if current_url in visited_urls:
                queue.task_done()
                continue
            visited_urls.add(current_url)

        # Sleep to avoid overwhelming the server
        time.sleep(random.uniform(2, 4))

        # Fetch the page content
        try:
            response = requests.get(current_url, timeout=5)
            response.raise_for_status()  # Check for request errors
            content = response.content

            # Parse the fetched content to find new URLs
            webpage = BeautifulSoup(content, "html.parser")

            # Parsing URLS
            hyperlinks = webpage.select("a[href]")
            new_urls = parse_links(hyperlinks, current_url)

            with lock:
                for new_url in new_urls:
                    if new_url not in visited_urls:
                        queue.put(new_url)
                crawl_count[0] += 1

            # Index the webpage
            indexed_page = index_page(webpage, current_url)
            # print(f"Indexing: {indexed_page['url']}")

            # Add the indexed page to indexed_pages list
            with lock:
                indexed_pages.append(indexed_page)  # Add to the indexed_pages list

        # Handle HTTP errors
        except requests.RequestException as e:
            print(f"Failed to fetch {current_url}: {e}")
        finally:
            queue.task_done()

# Function to parse links from HTML content
def parse_links(hyperlinks, current_url):
    urls = []
    for hyperlink in hyperlinks:
        url = hyperlink["href"]

        # Format the URL into a proper URL
        if url.startswith("#"):
            continue  # Skip same-page anchors
        if url.startswith("//"):
            url = "https:" + url  # Add scheme to protocol-relative URLs
        elif url.startswith("/"):
            # Construct full URL for relative links
            base_url = "{0.scheme}://{0.netloc}".format(requests.utils.urlparse(current_url))
            url = base_url + url
        elif not url.startswith("http"):
            continue  # Skip non-HTTP links
        url = url.split("#")[0]  # Remove anchor
        urls.append(url)
    return urls

def fooglebot(args=None, starting_urls=None):
    starting_urls = [
        "https://en.wikipedia.org/wiki/Google",
        "https://en.wikipedia.org/wiki/Microsoft",
        "https://en.wikipedia.org/wiki/OpenAI"
    ] if starting_urls is None else starting_urls

    urls_to_crawl = Queue()
    for seed in starting_urls:
        urls_to_crawl.put(seed)

    visited_urls = set()
    crawl_count = [0]
    CRAWL_LIMIT = 100
    lock = threading.Lock()
    stop_crawl = threading.Event()
    indexed_pages = []

    args = {
        'queue': urls_to_crawl,
        'visited_urls': visited_urls if args is None else args['visited_urls'],
        'crawl_count': crawl_count,
        'CRAWL_LIMIT': CRAWL_LIMIT if args is None else args['CRAWL_LIMIT'],
        'lock': lock,
        'stop_crawl': stop_crawl,
        'indexed_pages': indexed_pages if args is None else args['indexed_pages']
    }

    NUM_WORKERS = 20
    with ThreadPoolExecutor(max_workers=NUM_WORKERS) as executor:
        for _ in range(NUM_WORKERS):
            executor.submit(crawl, args)

    print("Crawling finished.")
    return indexed_pages, args

if __name__ == "__main__":
    indexed_pages, args = fooglebot()
    print("Indexed pages:", indexed_pages)