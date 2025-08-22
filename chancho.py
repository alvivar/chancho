from datetime import datetime, timezone
from playwright.sync_api import sync_playwright
import json
import sys


DB_FILE = "chandb.json"
USER_AGENT = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"


def get_links(urls: list[str]) -> list[tuple[str, str, list[str]]]:
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


def get_db():
    try:
        with open(DB_FILE, "r", encoding="utf-8") as f:
            db = json.load(f)
    except Exception:
        db = {}
    return db


def update_db(db, url_title_links: list[tuple[str, str, list[str]]]):
    current_time = datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")

    for url, title, links in url_title_links:
        if url in db:
            entry = db[url]

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


def print_instructions():
    print("chancho <thread_url> [thread_url2] ...")
    print("chancho --list-threads")
    print("chancho --list-info")


if __name__ == "__main__":
    CHANCHO = """
      ___&
    e'^_ )
      " " """
    print(CHANCHO)

    db = get_db()

    if len(sys.argv) < 2:
        print_instructions()
        print()
        sys.exit(1)

    # Commands

    commands = " ".join(sys.argv[1:])
    command_used = False

    if "--list-threads" in commands and "--list-info" not in commands:
        command_used = True
        for url in db:
            print(url)
        print()

    if "--list-info" in commands:
        command_used = True
        for url, entry in db.items():
            print(url)
            print(entry["title"])
            links = entry["links"]
            pending = len(links["pending"])
            downloaded = len(links["downloaded"])
            failed = len(links["failed"])
            print(f"{downloaded} downloaded, {pending + failed} pending")
            print()

    if "--total" in commands:
        command_used = True

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

    if command_used:
        sys.exit(0)

    # Scan

    thread_urls = sys.argv[1:]
    thread_urls = sorted(list(set(thread_urls)))

    try:
        results = get_links(thread_urls)
    except Exception:
        print_instructions()
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
