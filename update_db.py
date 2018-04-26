import csv
import json
import os
import progressbar
import re
import sqlite3
import sys
import datetime # must be after sqlite3

from xlrd import open_workbook  # Excel files

csv.field_size_limit(sys.maxsize)

# Make sure missing barcodes aren't just checked out
CHECKED_OUT_BARCODES = [str(int(x.strip())) for x in open("../checked_out/checkedout_since_greenglass.txt").read().split("\n")]
GG_CALLNUMBERS = open("../gg_archive/gg_callnumbers.txt", "r").read().split("\n")

# Load map of barcodes to callnumber sections
BARCODE_CN_MAP = json.load(open("../db_data/barcode_cn_map.json", "r"))
POSTED_CN_MAP = json.load(open("../db_data/posted_cn_map.json", "r"))
POSTED_COUNTS = {}
REVIEWED_COUNTS = {}

conn = sqlite3.connect("../database.sqlite")

def make_unique(arr):
    return list(set(filter(None, arr)))

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

FILE_BARCODE_INDEX = {}
def parse_crtf_dir(reports_dir):
    c = conn.cursor()
    c.execute("SELECT id,initials FROM librarians")

    assignments = {}
    lib = c.fetchone()
    while lib:
        id, initials = lib
        assignments[initials] = id
        lib = c.fetchone()

    for dirpath, dirnames, filenames in os.walk(reports_dir):
        for filename in filenames:
            barcodes = []

            # Determine associated librarian
            created_by = -1
            for initials in assignments:
                if "_%s_" % initials in filename:
                    created_by = assignments[initials]
                    break
            if created_by == -1:
                print ("initials missing from %s" % filename)
                continue

            with open_workbook(os.path.join(dirpath, filename)) as book:
                sheet = book.sheet_by_index(0)
                rvalues = sheet.row_values(0)

                # Get posted_file id
                c.execute("SELECT id FROM posted_files WHERE name=?", (filename,))
                file_id = c.fetchone()

                if file_id:
                    file_id = file_id[0]
                else:
                    # Make new posted_file
                    c.execute(
                        "INSERT INTO posted_files(name, created_by, item_count) VALUES (?,?,?);",
                        (filename, created_by, sheet.nrows - 1)
                    )
                    file_id = c.lastrowid

                print ("\t%s (%d)" % (filename, file_id))

                # Find barcode column
                bc_column = -1
                cn_column = -1
                if "Barcode" in rvalues:
                    bc_column = rvalues.index("Barcode")
                    cn_column = rvalues.index("Display Call Number")
                else:
                    bc_column = int(input("\nWhich col correspond to Barcode? >: "))

                check_letter = filename[0]
                ref_barcode = False
                first_callnumber = False
                last_callnumber = False
                for row in range(1, sheet.nrows):
                    # Save all barcodes
                    rvalues = sheet.row_values(row)
                    barcode = str(rvalues[bc_column]).strip().split(".")[0] # Remove decimaled barcodes
                    if len(barcode) == 0:
                        continue
                    barcodes.append(barcode)
                    section = POSTED_CN_MAP[barcode]
                    if not section in POSTED_COUNTS:
                        POSTED_COUNTS[section] = 1
                    else:
                        POSTED_COUNTS[section] += 1

                    # Count reviewed items
                    callnumber = normalize_callnumber(rvalues[cn_column])
                    if check_letter == callnumber[0]:
                        if first_callnumber == False or callnumber < first_callnumber:
                            first_callnumber = callnumber
                            ref_barcode = barcode
                        if last_callnumber == False or callnumber > last_callnumber:
                            last_callnumber = callnumber
                # Calculate library retention
                first_index = GG_CALLNUMBERS.index(first_callnumber)
                last_index = GG_CALLNUMBERS.index(last_callnumber)
                section = BARCODE_CN_MAP[ref_barcode]
                if not section in REVIEWED_COUNTS:
                    REVIEWED_COUNTS[section] = last_index - first_index + 1 # inclusive
                else:
                    REVIEWED_COUNTS[section] += last_index - first_index + 1

            # Make barcodes unique
            barcodes = make_unique(barcodes)
            # Save index limit for file
            FILE_BARCODE_INDEX[len(POSTED_BARCODES) + len(barcodes)] = file_id
            # Save barcodes to global
            POSTED_BARCODES.extend(barcodes)
    conn.commit()

def parse_request(row):
    global CHECKED_OUT_BARCODES, FILE_BARCODE_INDEX, POSTED_BARCODES

    c = conn.cursor()

    # Get faculty name
    lines = row[4].split('\n')
    current = 0
    faculty_name = ""
    while lines[current] != 'Faculty First Name:':
        current += 1
    faculty_name = lines[current + 1]

    while lines[current] != 'Faculty Last Name:':
        current += 1
    faculty_name += ' ' + lines[current + 1]

    # Get id
    c.execute("SELECT id FROM faculty WHERE name=? LIMIT 1", (faculty_name,))
    faculty_id = c.fetchone()

    if faculty_id:
        faculty_id = faculty_id[0]
    else:
        # Make new faculty member
        while lines[current] != 'Faculty Department:':
            current += 1
        department = lines[current + 1]

        while lines[current] != 'Campus Address:':
            current += 1
        address = lines[current + 1]

        c.execute(
            "INSERT INTO faculty(name, department, address) VALUES (?,?,?);",
            (faculty_name, department, address)
        )
        faculty_id = c.lastrowid

    # Get request id
    request_date = datetime.datetime.strptime(row[0], "%b %d, %Y, %I:%M:%S %p")

    c.execute("SELECT id FROM faculty_requests WHERE faculty=? AND date=?", (faculty_id, request_date))
    request_id = c.fetchone()

    if request_id:
        request_id = request_id[0]
    else:
        c.execute(
            "INSERT INTO faculty_requests(faculty, date) VALUES (?,?);",
            (faculty_id, request_date)
        )
        request_id = c.lastrowid

    form_month = request_date.strftime("%B %Y")

    parts = row[4].split("Barcode:\n")
    book_submissions = parts[1:]
    first_barcode = True
    for bt in book_submissions:
        bc = 0
        blines = bt.split('\n')
        barcode = blines[0].strip()

        # Skip if in database
        c.execute("SELECT 1 FROM book_requests WHERE barcode=? AND request=?", (barcode,request_id))
        if c.fetchone():
            continue

        while blines[bc] != 'Destination:':
            bc += 1
        personal = blines[bc + 1].strip() == 'Patron'

        while blines[bc] != 'Comment:':
            bc += 1
        comment = '\n'.join(blines[bc + 1:]).strip()

        if barcode in POSTED_BARCODES:
            # Identify file
            index = POSTED_BARCODES.index(barcode)
            from_file = -1
            for limit in FILE_BARCODE_INDEX:
                if index < limit:
                    from_file = FILE_BARCODE_INDEX[limit]
                    break
            # Save request
            c.execute(
                "INSERT INTO book_requests(barcode, cn_section, personal, comment, request, from_file) VALUES (?,?,?,?,?,?);",
                (barcode, BARCODE_CN_MAP[barcode], personal, comment, request_id, from_file)
            )
        elif not barcode in CHECKED_OUT_BARCODES:
            print ("\tmissing barcode: %s (%s)" % (barcode, row[0]))
    conn.commit()

POSTED_BARCODES = []
weeding_dirs = [dir.path for dir in os.scandir("../sources/") if dir.is_dir()]
print ("Gathering All Weeding Data...")
for dir in weeding_dirs:
    print (dir)
    parse_crtf_dir(dir)

# Callnumbers reviewed
c = conn.cursor()
for section in POSTED_COUNTS:
    c.execute("UPDATE callnumbers SET posted_count=? WHERE section=?", (POSTED_COUNTS[section], section))
for section in REVIEWED_COUNTS:
    c.execute("UPDATE callnumbers SET reviewed_count=? WHERE section=?", (REVIEWED_COUNTS[section], section))

print ("\nParsing Requests...")
file = csv.reader(open("input.csv", encoding="utf-8"))
form_rows = []
header = True
for row in file:
    if header: # skip header
        header = False
        continue
    form_rows.append(row)
# Sort by date
form_rows.sort(key=lambda r: datetime.datetime.strptime(r[0], "%b %d, %Y, %I:%M:%S %p"))
# Parse all requests
bar = progressbar.ProgressBar(max_value=len(form_rows))
index = 0
for row in form_rows:
    parse_request(row)
    index += 1
    bar.update(index)
bar.finish()

conn.commit()
conn.close()
