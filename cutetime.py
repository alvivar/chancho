"""
    Library to transform between seconds and a particular string
    representation.

    The main idea is being able to express time written as a number with a
    letter that represents the quantity.

    e.g
        "1h" -> 3600s
        "2m" -> 120s
        "30s" | "30" -> 30s
        "30sm" -> None (Only one symbol)
        "1d" -> 86400s (1 day)
        "5x" -> None (x is not a valid symbol)
        "2h30m10" -> 7200s + 1800s + 10


    TODO
        Years
"""

import re


def toseconds(strtime):
    """
        Return the seconds represented in 'strtime' based on the special
        convention. 'default' will be returned if 'strtime' is malformed.

        e.g
            "1h" -> 3600s
            "2m" -> 120s
            "30s" | "30" -> 30s
            "30sm" -> 0 (Only one symbol per number)
            "1d" -> 86400s (1 day)
            "5x" -> 0 (x is not a valid symbol)
            "2h30m10" -> 7200s + 1800s + 10s
    """

    result = 0

    for i in re.split(r"([0-9]+[a-z]+)", strtime):

        stri = i.strip().lower()  # Case insensitive
        if not stri:
            continue

        digits = "".join([i for i in stri if i.isdigit()])

        if len(stri) == len(digits):  # Without symbol assume seconds
            result += int(digits)
        elif len(stri) > len(digits) + 1:  # Only one symbol number
            result += 0
        elif 'd' in stri:  # Days
            result += 86400 * int(digits)
        elif 'h' in stri:  # Hours
            result += 3600 * int(digits)
        elif 'm' in stri:  # Minutes
            result += 60 * int(digits)
        elif 's' in stri:  # Seconds
            result += int(digits)

    return result


def tostr(seconds):
    """
        Return a str representation of 'seconds' based on the special convention.

        e.g
            100 -> "2m40s"
            1000 -> "17m40s"
            10000 -> "3h47m40s"
            100000 -> "1d3h46m40s"

        TODO
            Years
    """

    seconds = abs(seconds)
    days = hours = minutes = 0

    if seconds >= 86400:
        days = seconds / 86400
        seconds = (days - int(days)) * 86400

    if seconds >= 3600:
        hours = seconds / 3600
        seconds = (hours - int(hours)) * 3600

    if seconds >= 60:
        minutes = seconds / 60
        seconds = (minutes - int(minutes)) * 60

    strtime = ""
    strtime += f"{int(days)}d" if days else ""
    strtime += f"{int(hours)}h" if hours else ""
    strtime += f"{int(minutes)}m" if minutes else ""
    strtime += f"{round(seconds)}s" if seconds else ""

    return strtime if strtime else "0s"


if __name__ == '__main__':

    # Tests

    print(toseconds("1h1d"))
    print(tostr(90000))
