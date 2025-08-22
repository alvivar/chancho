from datetime import datetime, timezone
import json
from playwright.sync_api import sync_playwright
import sys


USER_AGENT = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
DOWNLOAD_FILE = "chanlist.json"


def get_links(thread_urls: list[str]) -> list[tuple[str, str, list[str]]]:
    results = []
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        context = browser.new_context(user_agent=USER_AGENT)

        for thread_url in thread_urls:
            page = context.new_page()
            page.goto(thread_url)

            hrefs = page.evaluate("""
                () => {
                    const links = Array.from(document.querySelectorAll('a[href*="4cdn"]'));
                    return [...new Set(links.map(link => link.href))].sort();
                }
            """)

            title = page.title()
            page.close()

            results.append((thread_url, title, hrefs))

        browser.close()

        return results


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python chancho.py <thread_url> [thread_url2] ...")
        sys.exit(1)

    try:
        with open(DOWNLOAD_FILE, "r", encoding="utf-8") as f:
            db = json.load(f)
    except FileNotFoundError:
        db = {}

    thread_urls = sys.argv[1:]
    results = get_links(thread_urls)

    current_time = datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")

    for thread_url, title, links in results:
        if thread_url in db:
            entry = db[thread_url]
            entry["title"] = title
            entry["updated"] = current_time

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
                entry["links"]["pending"].extend(new_links)
        else:
            db[thread_url] = {
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

    with open(DOWNLOAD_FILE, "w", encoding="utf-8") as f:
        json.dump(db, f, indent=4, ensure_ascii=False)

    for thread_url, title, links in results:
        print(title)
        print(thread_url)
        print()
        for link in links:
            print(link)
        print()
