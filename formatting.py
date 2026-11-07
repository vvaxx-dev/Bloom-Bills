
SUFFIXES = ["", "K", "M", "B", "T", "Qa", "Qi", "Sx", "Sp", "Oc", "No", "Dc"]


def fmt(n):
    """1234567 -> '1.23M'. Falls back to scientific notation (1.23e45) past Dc."""
    n = int(n)
    if n < 0:
        return "-" + fmt(-n)
    if n < 10000:
        return str(n)
    s = str(n)
    digits = len(s)
    exp = (digits - 1) // 3
    if exp < len(SUFFIXES):
        head = digits - exp * 3
        whole, frac = s[:head], s[head:head + 2].rstrip("0")
        return whole + ("." + frac if frac else "") + SUFFIXES[exp]
    frac = s[1:3].rstrip("0")
    return s[0] + ("." + frac if frac else "") + "e" + str(digits - 1)


def clock(seconds):
    seconds = max(0, int(seconds + 0.999))
    return "%d:%02d" % (seconds // 60, seconds % 60)
