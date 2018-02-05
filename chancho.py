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

import cutetime


def download_4chan_thread(threadurl, path):
    """
        Downloads all images from a thread. Return a tuple with 2 lists, one of
        downloaded urls, the other of previously downloaded.
    """
    thread_name = threadurl.split("/")[-1]
    download_dir = os.path.join(path, "downloads", thread_name)

    images = get_4chan_images(threadurl)
    now, previously = download_urls(images, download_dir)

    if now or previously:
        print(f"Thread {thread_name} complete!")
    else:
        print(f"Invalid thread (no images): {threadurl}")

    return now, previously


def get_4chan_images(threadurl):
    """
        Return a list with all the images urls from a thread.
    """

    try:
        page = requests.get(threadurl)
        tree = html.fromstring(page.content)
        pics = tree.xpath("//div[contains(@class, 'fileText')]/a/@href")
    except requests.exceptions.MissingSchema:
        print(f"Invalid url: {threadurl}")
        return []

    return ["http://" + i[2:] for i in pics]


def get_threads_from_board(board, baseurl='http://boards.4chan.org'):
    """
        Return a list with all the threads urls from a board, ignoring sticky
        posts.
    """
    board_url = f"{baseurl}/{board}"
    page = requests.get(board_url)
    tree = html.fromstring(page.content)
    threads = tree.xpath(
        "//div[@class='board']/div[@class='thread' and not(.//img[@alt='Sticky'])]/@id"
    )
    return [f"{baseurl}/{board}/thread/{t[1:]}" for t in threads]


def download_urls(urls, download_dir=""):
    """
        Downloads files from a list of urls. Return a tuple with 2 lists, one
        of downloaded urls, the other of previously downloaded.
    """

    # It needs to be something
    if not urls:
        return [], []

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

            # Save
            with open(before_file, "w") as f:
                json.dump(downloaded + downloaded_before, f)

        except urllib.error.HTTPError:
            print(f"Error downloading {url}")

    return downloaded, downloaded_before


if __name__ == "__main__":

    CHANCHO = """
      ___&
    e'^_ )
      " " """
    print(CHANCHO)

    # Command line
    PARSER = argparse.ArgumentParser(
        description=
        "4chan image downloader that keeps watching threads for new changes")
    PARSER.add_argument(
        "-s", "--start", help="start the cycle", action="store_true")
    PARSER.add_argument(
        "-t",
        "--threads",
        help="add threads urls to the download list",
        nargs="+",
        default=[])
    PARSER.add_argument(
        "-b",
        "--boards",
        help=
        "add boards names to be watched, the top thread from each board will be added to the download list after every cycle",
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
        help="archive old threads, 3600 seconds (1h) default",
        nargs="?",
        type=int,
        const=3600)
    ARGS = PARSER.parse_args()

    # --start is required
    if not ARGS.start:
        print("try -s to start the cycle")
        PARSER.print_usage()
        PARSER.exit()

    # frozen / not frozen, cxfreeze compatibility
    HOMEDIR = os.path.normpath(
        os.path.dirname(
            sys.executable if getattr(sys, 'frozen', False) else __file__))

    # Files
    THREAD_FILE = os.path.join(HOMEDIR, "chanlist.json")
    PRUNE_FILE = os.path.join(HOMEDIR, "pruned.json")

    # Repeat cycle and input detection
    REPEAT = True

    def botmode():
        """
            Handles the user input.
        """
        while True:
            text = input()
            text = text.strip().lower()
            commands = text.split()

            if len(commands) < 1:
                return
            commands[0] = commands[0].replace('-', '')

            # Quit
            if commands[0] == 'q':
                print(CHANCHO + " Bye!")
                time.sleep(1)

                global REPEAT
                REPEAT = False
                sys.exit(0)

            # Start
            elif commands[0] in ['s', 'start']:
                print("chancho: i'm already running!")

            # Help
            elif commands[0] in ['h', 'help']:
                PARSER.print_help()

            # Threads
            elif commands[0] in ['t', 'thread', 'threads']:
                ARGS.threads += commands[1:] if len(commands) > 1 else []
                print(f"chancho: adding threads: {' '.join(commands[1:])}")

            # Boards
            elif commands[0] in ['b', 'board', 'boards']:
                ARGS.boards += commands[1:] if len(commands) > 1 else []
                print(f"chancho: adding boards: {', '.join(commands[1:])}")

            # Wait
            elif commands[0] in ['w', 'wait']:
                ARGS.wait = cutetime.toseconds(
                    commands[1]) if len(commands) > 1 else 60
                print(f"chancho: wait time is {ARGS.wait}s now")

            # Prune
            elif commands[0] in ['p', 'prune']:
                ARGS.prune = cutetime.toseconds(
                    commands[1]) if len(commands) > 1 else 3600
                print(f"chancho: prune time is {ARGS.prune}s now")

            else:
                print(f"chancho: i don't understand '{commands[0]}', try")
                PARSER.print_usage()

            print()

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
                thread for board in ARGS.boards
                for thread in get_threads_from_board(board)[:1]
            ]

            if TOP_THREADS:
                print(f"Top thread found: {TOP_THREADS[0]}")

        # Add the --threads, the input from the bot and the top threads from --boards
        for u in ARGS.threads + TOP_THREADS:
            # TODO validate url
            DOWNLOAD_LIST[u] = DOWNLOAD_LIST.get(u, {})

        # Download everything, update statistics
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
        print(f"\nWaiting {ARGS.wait} seconds to retry...")
        print("Feed me commands | 'q' to quit: ")

        WAIT = 0
        while REPEAT and WAIT < ARGS.wait:
            WAIT += 1
            time.sleep(1)
