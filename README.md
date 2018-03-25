```
      ___&
    e'^_ )
      " "
usage: chancho.py [-h] [-t THREADS [THREADS ...]] [-b BOARDS [BOARDS ...]]
                  [-r REPEAT] [-p PRUNE] [-w WAIT]

4chan image downloader that keeps watching threads for new changes

optional arguments:
  -h, --help            show this help message and exit
  -t THREADS [THREADS ...], --threads THREADS [THREADS ...]
                        threads urls to the download list
  -b BOARDS [BOARDS ...], --boards BOARDS [BOARDS ...]
                        boards names to be scanned, the top thread from each
                        board will be added to the download list every cycle
  -r REPEAT, --repeat REPEAT
                        seconds to wait between repeating the complete cycle
  -p PRUNE, --prune PRUNE
                        seconds old to archive threads
  -w WAIT, --wait WAIT  seconds to rest between threads downloads (default 3s)
```
