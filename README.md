# chancho

````
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
  --download      scans again and downloads all pending files```

Chancho is a 4chan thread downloader. It creates a `chandb.json` file as a registry for tracking files.

## Setup

Install dependencies using `requirements.txt`, then install [Playwright](https://playwright.dev/python/docs/intro):

```bash
playwright install
````
