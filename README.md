# chancho

```
      ___&
    e'^_ )
      " "
usage: chancho <thread_url> [thread_url2] ... [options]

4chan thread scraper

positional arguments:
  thread_urls     thread urls to scan

options:
  -h, --help      show this help message and exit
  --list-threads  list all tracked thread urls
  --list-info     list detailed information about all threads
  --total         show total statistics
  --scan          scan all existing threads in addition to provided urls
  --download      downloads all pending files
  --prune         prune all 404 threads
  --validate      validate all downloaded files
```

Chancho is a 4chan thread downloader. It tracks files in `chandb.json` in the working directory and stores downloads under `downloads/`.

## Setup

Install Python dependencies:

    pip install -r requirements.txt

Then install the headless browser used by Playwright:

    playwright install
