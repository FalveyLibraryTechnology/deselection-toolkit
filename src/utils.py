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
    norm = normalize(dot_collapsed)
    if not norm:
        raise ValueError("cannot normalize: %s" % callnumber)
    return norm
