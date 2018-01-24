"""
    CHANCHO is a 4chan image downloader
    that keeps watching threads for new changes
"""

import argparse
import json
import os
import sys
import threading
import time
import urllib

import requests
from lxml import html


def download_4chan_thread(thread_url, path):
    """
        Downloads all images from a thread. Return a tuple with 2 lists, one of
        downloaded urls, the other of previously downloaded.
    """
    thread_name = thread_url.split("/")[-1]
    download_dir = os.path.join(path, "downloads", thread_name)

    images = get_4chan_images(thread_url)
    now, previously = download_urls(images, download_dir)
    print(f"Thread {thread_name} complete!")

    return now, previously


def get_4chan_images(thread_url):
    """
        Return a list with all the images urls from a thread.
    """
    page = requests.get(thread_url)
    tree = html.fromstring(page.content)
    pics = tree.xpath("//div[contains(@class, 'fileText')]/a/@href")
    return ["http://" + i[2:] for i in pics]


def get_threads_from_board(board):
    """
        Return a list with all the url threads from a board, ignoring sticky
        posts.
    """
    board_url = f"http://boards.4chan.org/{board}"
    page = requests.get(board_url)
    tree = html.fromstring(page.content)
    threads = tree.xpath(
        "//div[@class='board']/div[@class='thread' and not(.//img[@alt='Sticky'])]/@id"
    )
    return [f"http://boards.4chan.org/{board}/thread/{t[1:]}" for t in threads]


def download_urls(urls, download_dir=""):
    """
        Downloads files from a list of urls. Return a tuple with 2 lists, one
        of downloaded urls, the other of previously downloaded.
    """

    # Create the dir
    if download_dir and not os.path.exists(download_dir):
        os.makedirs(download_dir)

    downloaded_before = []
    before_file = os.path.join(download_dir, "done.json")
    if os.path.isfile(before_file):
        with open(before_file) as f:
            downloaded_before = json.load(f)

    # Ignore downloaded before
    urls = [i for i in urls if i not in downloaded_before]

    # Download
    downloaded = []
    for i, url in enumerate(urls):
        name = url.split("/")[-1]
        filename = os.path.join(download_dir, name)
        print(f"Downloading {i+1}/{len(urls)} {url}")

        try:
            with urllib.request.urlopen(url) as r, open(filename, 'wb') as f:
                data = r.read()
                f.write(data)
            downloaded.append(url)
        except urllib.error.HTTPError:
            print(f"Error downloading {url}")

        # Save
        with open(before_file, "w") as f:
            json.dump(downloaded + downloaded_before, f)

    return downloaded, downloaded_before


if __name__ == "__main__":

    print("""
      ___&
    e'^_ )
      " " """)

    # Command line
    PARSER = argparse.ArgumentParser()
    PARSER.add_argument(
        "-t",
        "--threads",
        help="add threads to the download list",
        nargs="+",
        default=[])
    PARSER.add_argument(
        "-b",
        "--boards",
        help="add the top thread from each boards to the download list",
        nargs="+",
        default=[])
    PARSER.add_argument(
        "-w",
        "--wait",
        help="seconds to wait between full downloads, 60 seconds default",
        default=60,
        type=int)
    PARSER.add_argument(
        "-p",
        "--prune",
        help="archive old threads, 3600 seconds default (1h)",
        nargs="?",
        type=int,
        const=3600)
    PARSER.add_argument("--bot", help="Feed me threads", action="store_true")
    ARGS = PARSER.parse_args()

    # frozen / not frozen, cxfreeze compatibility
    HOMEDIR = os.path.normpath(
        os.path.dirname(
            sys.executable if getattr(sys, 'frozen', False) else __file__))

    # Files
    THREAD_FILE = os.path.join(HOMEDIR, "chanlist.json")
    PRUNE_FILE = os.path.join(HOMEDIR, "pruned.json")

    # BOT mode
    REPEAT = True
    BOT_URLS = []

    if ARGS.bot:

        def botmode():
            """
                Handles the user input.
            """
            while True:
                text = input()

                text = text.strip().lower()

                if text == 'q':
                    print("Bye!")
                    global REPEAT
                    REPEAT = False
                    sys.exit(0)
                else:
                    global BOT_URLS
                    BOT_URLS += [text]

        THREAD = threading.Thread(target=botmode)
        THREAD.daemon = True
        THREAD.start()

    # Downloads
    while REPEAT:

        # Read the queue
        DOWNLOAD_LIST = {}
        if os.path.isfile(THREAD_FILE):
            with open(THREAD_FILE) as f:
                DOWNLOAD_LIST = json.load(f)

        # --boards Top threads
        TOP_THREADS = []
        if (ARGS.boards):
            TOP_THREADS = [
                thread
                for board in ARGS.boards
                for thread in get_threads_from_board(board)[:1]
            ]

            if TOP_THREADS:
                print(f"Top thread found: {TOP_THREADS[0]}")

        # Add the --threads, the input from the bot and the top threads from --boards
        for u in ARGS.threads + BOT_URLS + TOP_THREADS:
            # TODO validate url
            DOWNLOAD_LIST[u] = DOWNLOAD_LIST.get(u, {})
        BOT_URLS = []

        # Exit on empty
        if not DOWNLOAD_LIST:

            # --bot
            if ARGS.bot:
                continue

            PARSER.print_usage()
            print("the download list is empty, try '-u' to add urls")
            PARSER.exit()

        # Download everything, update statistics
        else:
            for k, v in DOWNLOAD_LIST.items():
                down_now, down_previously = download_4chan_thread(k, HOMEDIR)
                v['images'] = len(down_now) + len(down_previously)
                if down_now:
                    v['found'] = time.time()
                    v['prune'] = 0
                else:
                    # Hack to avoid weird prune values when the field doesn't
                    # exist on already downloaded threads
                    v['found'] = v.get('found', time.time())

                    prune = time.time() - v['found']
                    v['prune'] = prune if prune > 0 else 0

                # Save
                with open(THREAD_FILE, "w") as f:
                    json.dump(DOWNLOAD_LIST, f)

        # --prune
        if ARGS.prune:

            # Read archive
            PRUNE_LIST = {}
            if os.path.isfile(PRUNE_FILE):
                with open(PRUNE_FILE) as f:
                    PRUNE_LIST = json.load(f)

            # Clean up current, archive prune
            CLEAN_DOWNLOAD_LIST = {}
            for k, v in DOWNLOAD_LIST.items():
                if v.get('prune', 0) > ARGS.prune:
                    PRUNE_LIST[k] = v
                else:
                    CLEAN_DOWNLOAD_LIST[k] = v
            PRUNE_COUNT = len(DOWNLOAD_LIST) - len(CLEAN_DOWNLOAD_LIST)
            DOWNLOAD_LIST = CLEAN_DOWNLOAD_LIST

            if PRUNE_COUNT > 0:
                print(f"{PRUNE_COUNT} thread{'s' if PRUNE_COUNT > 1 else ''} "
                      f"pruned ({ARGS.prune}s old)")

            # Save
            with open(PRUNE_FILE, "w") as f:
                json.dump(PRUNE_LIST, f)

            with open(THREAD_FILE, "w") as f:
                json.dump(DOWNLOAD_LIST, f)

            # Nothing else to do
            if len(DOWNLOAD_LIST) < 1:
                print()
                continue

        # --rest between complete downloads
        print(f"Waiting {ARGS.wait}s to retry")

        if ARGS.bot:
            print("Feed me threads urls | 'q' to exit:")

        WAIT = 0
        while REPEAT and WAIT < ARGS.wait:
            WAIT += 1
            time.sleep(1)
