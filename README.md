```
      ___&
    e'^_ )
      " "
usage: chancho.py [-h] [-t THREADS [THREADS ...]] [-b BOARDS [BOARDS ...]]
                  [-w WAIT] [-p [PRUNE]]

4chan image downloader that keeps watching threads for new changes

optional arguments:
  -h, --help            show this help message and exit
  -t THREADS [THREADS ...], --threads THREADS [THREADS ...]
                        add threads to the download list
  -b BOARDS [BOARDS ...], --boards BOARDS [BOARDS ...]
                        add the top thread from each boards to the download
                        list
  -w WAIT, --wait WAIT  seconds to wait between full downloads, 60 seconds
                        default
  -p [PRUNE], --prune [PRUNE]
                        archive old threads, 3600 seconds (1h) default
```
