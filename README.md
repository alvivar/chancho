```
      ___&
    e'^_ )
      " "
usage: chancho.py [-h] [-s] [-t THREADS [THREADS ...]]
                  [-b BOARDS [BOARDS ...]] [-w WAIT] [-p [PRUNE]]

4chan image downloader that keeps watching threads for new changes

optional arguments:
  -h, --help            show this help message and exit
  -s, --start           start the cycle
  -t THREADS [THREADS ...], --threads THREADS [THREADS ...]
                        add threads urls to the download list
  -b BOARDS [BOARDS ...], --boards BOARDS [BOARDS ...]
                        add boards names to be watched, the top thread from
                        each board will be added to the download list after
                        every cycle
  -w WAIT, --wait WAIT  seconds to wait between full downloads, 60 seconds
                        default
  -p [PRUNE], --prune [PRUNE]
                        archive old threads, 3600 seconds (1h) default
```
