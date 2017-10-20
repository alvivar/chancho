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
from multiprocessing import Queue  # cxfreeze fx

import requests
from lxml import _elementpath, html  # cxfreeze fx


def download_4chan_thread(thread_url, path):
    thread_name = thread_url.split("/")[-1]
    download_dir = os.path.join(path, "downloads", thread_name)

    images = get_4chan_images(thread_url)
    down_now, down_previously = download_urls(images, download_dir)

    print(f"Thread {thread_name} complete!")
    return down_now, down_previously


def get_4chan_images(thread_url):
    page = requests.get(thread_url)
    tree = html.fromstring(page.content)
    pics = tree.xpath("//div[contains(@class, 'fileText')]/a/@href")
    return ["http://" + i[2:] for i in pics]


def get_top_threads_from_board(board):
    """ Get all the top threads from a board, ignoring sticky posts. """
    board_url = f"http://boards.4chan.org/{board}"
    page = requests.get(board_url)
    tree = html.fromstring(page.content)
    threads = tree.xpath(
        "//div[@class='board']/div[@class='thread' and not(.//img[@alt='Sticky'])]/@id"
    )
    return [f"http://boards.4chan.org/{board}/thread/{t[1:]}" for t in threads]


# Returns a tuple with the last downloaded urls, and all the previously
# downloaded urls
def download_urls(urls, download_dir=""):

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

    # Command line args
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "-t",
        "--threads",
        help="add threads to the download list",
        nargs="+",
        default=[])
    parser.add_argument(
        "-b",
        "--boards",
        help="add the top thread from each boards to the download list",
        nargs="+",
        default=[])
    parser.add_argument(
        "-w",
        "--wait",
        help="seconds to wait between full downloads, 60 seconds default",
        default=60,
        type=int)
    parser.add_argument(
        "-p",
        "--prune",
        help="archive old threads, 3600 seconds default (1h)",
        nargs="?",
        type=int,
        const=3600)
    parser.add_argument("--bot", help="Feed me urls", action="store_true")

    args = parser.parse_args()

    # frozen / not frozen, cxfreeze compatibility
    current_dir = os.path.normpath(
        os.path.dirname(
            sys.executable if getattr(sys, 'frozen', False) else __file__))

    # Files
    threads_file = os.path.join(current_dir, "chanlist.json")
    prune_file = os.path.join(current_dir, "pruned.json")

    # BOT mode
    bot_urls = []

    if args.bot:
        print('Feed me threads:')

        def BOT():
            while True:
                text = input()
                global bot_urls
                bot_urls += [text]

        thread = threading.Thread(target=BOT)
        thread.daemon = True
        thread.start()

    # Downloads
    while True:

        # Read the queue
        download_list = {}
        if os.path.isfile(threads_file):
            with open(threads_file) as f:
                download_list = json.load(f)

        # --boards Top threads
        top_threads = []
        if (args.boards):
            top_threads = [
                thread
                for board in args.boards
                for thread in get_top_threads_from_board(board)[:1]
            ]

        # Add the --threads, the input from the bot and the top threads from --boards
        for u in args.threads + bot_urls + top_threads:
            # TODO validate url
            download_list[u] = download_list.get(u, {})
        bot_urls = []

        # Exit on empty
        if not download_list:

            # --bot
            if args.bot:
                continue

            parser.print_usage()
            print("the download list is empty, try '-u' to add urls")
            parser.exit()

        # Download everything, update statistics
        else:
            for k, v in download_list.items():
                down_now, down_previously = download_4chan_thread(
                    k, current_dir)
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
                with open(threads_file, "w") as f:
                    json.dump(download_list, f)

        # --prune
        if args.prune is not None:

            # Read archive
            prune_list = {}
            if os.path.isfile(prune_file):
                with open(prune_file) as f:
                    prune_list = json.load(f)

            # Clean up current, archive prune
            clean_download_list = {}
            for k, v in download_list.items():
                if v.get('prune', 0) > args.prune:
                    prune_list[k] = v
                else:
                    clean_download_list[k] = v
            prune_count = len(download_list) - len(clean_download_list)
            download_list = clean_download_list

            if prune_count > 0:
                print(f"{prune_count} thread{'s' if prune_count > 1 else ''} "
                      f"pruned ({args.prune}s old)")

            # Save
            with open(prune_file, "w") as f:
                json.dump(prune_list, f)

            with open(threads_file, "w") as f:
                json.dump(download_list, f)

            # Nothing else to do
            if len(download_list) < 1:
                print()
                continue

        # --rest between complete downloads
        print(f"Waiting {args.wait}s to retry")
        if args.bot:
            print("Feed me urls:")
        time.sleep(args.wait)
