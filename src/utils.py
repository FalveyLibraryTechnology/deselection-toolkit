import re
from .vendor.library_callnumber_lc import normalize


def comma(num):
    return '{:,}'.format(num)


def make_unique(arr):
    return list(set(filter(None, arr)))


def normalize_callnumber(callnumber):
    # Falvey customization: some callnumbers have .. instead of decimal
    # GN21..M36B37 1984
    # HQ1061. .W67 1984
    dot_collapsed = callnumber.replace(". .", ".").replace("..", ".")
    # Most failures are from improperly spaced groups
    letter_spaced = re.sub(r"([0-9])([a-zA-Z])", "\g<1> \g<2>", dot_collapsed)
    norm = normalize(letter_spaced)
    if not norm:
        raise ValueError("cannot normalize: %s (%s)" % (callnumber, letter_spaced))
    return norm
