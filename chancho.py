"""
CHANCHO is a 4chan image downloader
that keeps watching threads for new changes


TODO -d --directory To change the download directory
"""

import argparse
import json
import os
import time
import urllib

import requests
from lxml import html


def download_4chan_thread(thread_url):

    thread_name = thread_url.split("/")[-1]
    current_dir = os.path.normpath(os.path.dirname(__file__))
    download_dir = os.path.join(current_dir, "downloads", thread_name)

    images = get_4chan_images(thread_url)
    down_now, down_previously = download_urls(images, download_dir)

    print(f"Thread {thread_name} complete!")
    return down_now, down_previously


def get_4chan_images(thread_url):

    page = requests.get(thread_url)
    tree = html.fromstring(page.content)
    pics = tree.xpath("//div[contains(@class, 'fileText')]/a/@href")
    return ["http://" + i[2:] for i in pics]


# Returns a tuple with the last downloaded urls, and all the previously
# downloaded urls
def download_urls(urls, download_dir=""):

    # Create the dir
    if len(download_dir) > 0 and not os.path.exists(download_dir):
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
        "-u",
        "--url",
        help="4chan threads to be added to the download list",
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

    # ALT
    # if len(sys.argv[1:]) == 0:
    #     parser.print_usage()
    #     parser.exit()

    args = parser.parse_args()

    # Files
    current_dir = os.path.normpath(os.path.dirname(__file__))
    threads_file = os.path.join(current_dir, "chanlist.json")
    prune_file = os.path.join(current_dir, "pruned.json")

    # Downloads
    while True:

        # Read the queue
        download_list = {}
        if os.path.isfile(threads_file):
            with open(threads_file) as f:
                download_list = json.load(f)

        # Add the --url[s]
        for u in args.url:
            # TODO validate url
            download_list[u] = download_list.get(u, {})

        # Exit on empty
        if len(download_list) < 1:
            parser.print_usage()
            print("the download list is empty, try '-u' to add urls")
            parser.exit()
        # Download everything, update statistics
        else:
            for k, v in download_list.items():
                down_now, down_previously = download_4chan_thread(k)
                v['images'] = len(down_now) + len(down_previously)
                if len(down_now) > 0:
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
        time.sleep(args.wait)
