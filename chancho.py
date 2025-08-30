from datetime import datetime, timezone
from playwright.sync_api import sync_playwright
import argparse
import json
import os
import requests
import sys
import time


DB_FILE = "chandb.json"
DOWNLOAD_DIR = "downloads"
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

            print(url)
            print(title)
            print(f"{len(links)} files")
            print()

            results.append((url, title, links))

        browser.close()

        return results


def download_update_all(db):
    results = {}

    for url, entry in db.items():
        board, id = get_board_id(url)

        results[url] = {
            "downloaded": [],
            "failed": [],
        }

        once = False
        all_pending = sorted(entry["links"]["pending"] + entry["links"]["failed"])
        for link in all_pending:
            create_folders(board, id)

            success = download(
                link,
                os.path.join(DOWNLOAD_DIR, board, id, link.split("/")[-1]),
            )

            if success:
                results[url]["downloaded"].append(link)
                set_db_download(db, url, link, "downloaded")

                name = link.split("/")[-1]
                print(f"{board}/{id}/{name}")
                once = True

            else:
                results[url]["failed"].append(link)
                set_db_download(db, url, link, "failed")

            save_db(db)

        if once:
            print()

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
                print(f"{e}, attempt {attempt + 1}, retrying in {wait_time}s...")
                time.sleep(wait_time)
            else:
                print(f"{e}, after {max_retries} attempts")
                print()
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

            existing_links = set(
                entry["links"]["pending"]
                + entry["links"]["downloaded"]
                + entry["links"]["failed"]
            )

            new_links = [link for link in links if link not in existing_links]

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
                    "pending": links[:],
                    "downloaded": [],
                    "failed": [],
                },
            }


def set_db_download(db, thread_url, download_url, status):
    if thread_url not in db:
        return False

    links = db[thread_url]["links"]

    for link_list in links.values():
        if download_url in link_list:
            link_list.remove(download_url)

    if status in ["pending", "downloaded", "failed"]:
        links[status].append(download_url)
        return True

    return False


def update_db_downloads(db, results):
    for url, entry in results.items():
        new_downloaded = set(entry["downloaded"])
        new_failed = set(entry["failed"])

        links = db[url]["links"]
        pending = links["pending"]
        downloaded = links["downloaded"]
        failed = links["failed"]

        remaining_pending = []

        for link in pending:
            if link in new_downloaded:
                downloaded.append(link)
            elif link in new_failed:
                failed.append(link)
            else:
                remaining_pending.append(link)

        links["pending"] = remaining_pending


def prune(db):
    for url, entry in list(db.items()):
        if entry["pruned"]:
            print(url)
            print(entry["pruned"])
            print()
            del db[url]


def validate_downloads(db):
    for url, entry in db.items():
        board, thread_id = get_board_id(url)
        thread_folder = os.path.join(DOWNLOAD_DIR, board, thread_id)

        links = entry["links"]
        downloaded = links["downloaded"]
        pending = links["pending"]

        missing_files = []
        remaining_downloaded = []

        once = False
        for download_url in downloaded:
            filename = download_url.split("/")[-1]
            file_path = os.path.join(thread_folder, filename)

            if os.path.exists(file_path):
                remaining_downloaded.append(download_url)

            else:
                once = True
                print(f"{download_url}")
                missing_files.append(download_url)

        if once:
            print()

        links["downloaded"] = remaining_downloaded
        pending.extend(missing_files)


def save_db(db):
    with open(DB_FILE, "w", encoding="utf-8") as f:
        json.dump(db, f, indent=4, ensure_ascii=False)


def get_board_id(url):
    parts = url.split("/")  # https://boards.4chan.org/{board}/thread/{thread_id}
    board = parts[-3]
    thread_id = parts[-1]
    return board, thread_id


def create_folders(board, id):
    thread_folder = os.path.join(DOWNLOAD_DIR, board, id)
    os.makedirs(thread_folder, exist_ok=True)


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
        print(f"{downloaded} downloaded, {pending} pending, {failed} failed")
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

    parser.add_argument(
        "--download",
        action="store_true",
        help="downloads all pending files",
    )

    parser.add_argument(
        "--prune",
        action="store_true",
        help="prune all 404 threads",
    )

    parser.add_argument(
        "--validate",
        action="store_true",
        help="validate all downloaded files",
    )

    args = parser.parse_args()

    CHANCHO = """
      ___&
    e'^_ )
      " " """
    print(CHANCHO)

    db = get_db()

    # Commands

    if args.list_threads and not args.list_info:
        list_threads(db)

    if args.list_info:
        list_info(db)

    if args.total:
        show_total(db)

    # Maintenance

    if args.prune:
        prune(db)
        save_db(db)

    if args.validate:
        validate_downloads(db)
        save_db(db)

    # Scan

    thread_urls = args.thread_urls
    if args.scan:
        thread_urls.extend(db.keys())
    thread_urls = sorted(list(set(thread_urls)))

    if not (
        thread_urls
        or args.list_threads
        or args.list_info
        or args.total
        or args.download
        or args.prune
        or args.validate
    ):
        parser.print_help()
        print()
        sys.exit(1)
    try:
        # Update

        if thread_urls:
            results = get_links(thread_urls)
            update_db(db, results)
            save_db(db)

    except Exception as e:
        parser.print_help()
        print()
        print("Whoa, something went wrong.")
        print()
        print(str(e).strip())
        print()
        print("\n".join(thread_urls))
        print()
        sys.exit(1)

    # Download & Update

    if args.download:
        download_update_all(db)


if __name__ == "__main__":
    main()
