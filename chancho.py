from datetime import datetime, timezone
from playwright.sync_api import sync_playwright
import argparse
import json
import requests
import sys
import time


DB_FILE = "chandb.json"
USER_AGENT = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"


def get_links(urls):
    results = []
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        context = browser.new_context(user_agent=USER_AGENT)

        for url in urls:
            page = context.new_page()
            page.goto(url)

            links = page.evaluate("""
                () => {
                    const links = Array.from(document.querySelectorAll('a[href*="4cdn"]'));
                    return [...new Set(links.map(link => link.href))].sort();
                }
            """)

            title = page.title()
            page.close()

            results.append((url, title, links))

        browser.close()

        return results


def download(url, filename, max_retries=3):
    headers = {"User-Agent": USER_AGENT}

    for attempt in range(max_retries):
        try:
            response = requests.get(url, stream=True, headers=headers, timeout=30)
            response.raise_for_status()

            with open(filename, "wb") as f:
                for chunk in response.iter_content(chunk_size=8192):
                    if chunk:
                        f.write(chunk)

            return True

        except (requests.RequestException, IOError) as e:
            if attempt < max_retries - 1:
                wait_time = 2**attempt
                print(
                    f"Error downloading {url} (attempt {attempt + 1}): {e}. Retrying in {wait_time}s..."
                )
                time.sleep(wait_time)
            else:
                print(f"Error downloading {url} after {max_retries} attempts: {e}")
                return False


def get_db():
    try:
        with open(DB_FILE, "r", encoding="utf-8") as f:
            db = json.load(f)
    except Exception:
        db = {}
    return db


def update_db(db, url_title_links):
    current_time = datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")

    for url, title, links in url_title_links:
        if url in db:
            entry = db[url]

            if entry["pruned"]:
                continue

            if "404" in title and len(links) == 0:
                entry["pruned"] = current_time
                continue

            existing_links = {
                link["href"]
                for category_links in entry["links"].values()
                for link in category_links
            }

            new_links = [
                {"href": link, "found": current_time}
                for link in links
                if link not in existing_links
            ]

            if new_links:
                entry["updated"] = current_time
                entry["links"]["pending"].extend(new_links)
        else:
            db[url] = {
                "title": title,
                "found": current_time,
                "updated": current_time,
                "pruned": False,
                "links": {
                    "pending": [
                        {"href": link, "found": current_time} for link in links
                    ],
                    "downloaded": [],
                    "failed": [],
                },
            }


def save_db(db):
    with open(DB_FILE, "w", encoding="utf-8") as f:
        json.dump(db, f, indent=4, ensure_ascii=False)


def list_threads(db):
    for url in db:
        print(url)
    print()


def list_info(db):
    for url, entry in db.items():
        print(url)
        print(entry["title"])
        links = entry["links"]
        pending = len(links["pending"])
        downloaded = len(links["downloaded"])
        failed = len(links["failed"])
        print(f"{downloaded} downloaded, {pending + failed} pending")
        print()


def show_total(db):
    total_threads = len(db)
    total_pending = 0
    total_downloaded = 0
    total_failed = 0

    for entry in db.values():
        links = entry["links"]
        total_pending += len(links["pending"])
        total_downloaded += len(links["downloaded"])
        total_failed += len(links["failed"])

    print(f"Total threads: {total_threads}")
    print(f"Total downloaded: {total_downloaded}")
    print(f"Total pending: {total_pending}")
    print(f"Total failed: {total_failed}")
    print()


def main():
    parser = argparse.ArgumentParser(
        description="4chan thread scraper",
        usage="chancho <thread_url> [thread_url2] ... [options]",
    )

    parser.add_argument("thread_urls", nargs="*", help="thread urls to scan")

    parser.add_argument(
        "--list-threads", action="store_true", help="list all tracked thread urls"
    )

    parser.add_argument(
        "--list-info",
        action="store_true",
        help="list detailed information about all threads",
    )

    parser.add_argument("--total", action="store_true", help="show total statistics")

    parser.add_argument(
        "--scan",
        action="store_true",
        help="scan all existing threads in addition to provided urls",
    )

    args = parser.parse_args()

    CHANCHO = """
      ___&
    e'^_ )
      " " """
    print(CHANCHO)

    db = get_db()

    # Handle commands

    info_arg_used = False
    if args.list_threads and not args.list_info:
        info_arg_used = True
        list_threads(db)

    if args.list_info:
        info_arg_used = True
        list_info(db)

    if args.total:
        info_arg_used = True
        show_total(db)

    if info_arg_used:
        return

    # Scan mode

    thread_urls = args.thread_urls
    if args.scan:
        thread_urls.extend(db.keys())
    thread_urls = sorted(list(set(thread_urls)))

    if not thread_urls:
        parser.print_help()
        print()
        sys.exit(1)

    try:
        results = get_links(thread_urls)
    except Exception:
        parser.print_help()
        print()
        print("Whoa, something went wrong.")
        print("Check your thread URLs and arguments for errors.")
        print()
        print("\n".join(thread_urls))
        print()
        sys.exit(1)

    # Store

    update_db(db, results)
    save_db(db)

    # Print

    for url, title, links in results:
        print(url)
        print(title)
        print(f"{len(links)} files")
        print()


if __name__ == "__main__":
    main()
