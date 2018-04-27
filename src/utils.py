import re

def comma(num):
    return '{:,}'.format(num)

def normalize_callnumber(callnumber):
    section = re.search("^([A-Z]+)", callnumber).group(1)
    number_match = re.search("^[A-Z ]+([\d\.]+[ \.]*)", callnumber)
    number = number_match.group(1).strip(" .")
    rem = callnumber[number_match.end(1):]
    letter = re.search("^([A-Z]+)", rem)
    if letter == None:
        letter = " "
    else:
        letter = letter.group(1)
    extra = "".join([p.strip().ljust(12) for p in rem.split(" ")])
    num_str = "%05d" % (float(number) * 10000,)
    return ("%s %s %s %s" % (section.ljust(2), num_str.zfill(12), letter, extra)).strip()
