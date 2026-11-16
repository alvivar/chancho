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

The supported environment uses Python 3.14.10. Create it with Conda:

    conda env create -f environment.yml
    conda activate chancho

Alternatively, use an isolated Python 3.14.10 environment and install:

    python -m pip install -r requirements.txt

Install only the Chromium headless shell used by this app (Firefox, WebKit and
full Chromium are not needed):

    python -m playwright install chromium --only-shell

Run Chancho from the project directory:

    python chancho.py --help

## Environment maintenance

`requirements.txt` pins both direct and transitive runtime dependencies. Testing
plugins such as `pytest-playwright` are not required to run the app.

When upgrading, update the pins in `requirements.txt` and the Python version in
`environment.yml`, reinstall the dependencies, and repeat the browser install
command above. Playwright requires its matching browser revision; updating the
Python package alone is not enough.

Check dependency consistency after installation:

    python -m pip check

Playwright's browser cache is shared with other environments. Do not delete
browser directories needed by other projects.
