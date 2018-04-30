import csv
import json
import os
import progressbar
import re
import sqlite3
import sys
import datetime # must be after sqlite3

from xlrd import open_workbook  # Excel files

from src.posted_files import parse_source_file
from src.log_parsing import parse_request

csv.field_size_limit(sys.maxsize)

conn = sqlite3.connect("database.sqlite")

def addNewPostedFile():
    print ("Updating Weeding Data...")
    cursor = conn.cursor()
    weeding_dirs = [dir.path for dir in os.scandir("sources/") if dir.is_dir()]
    for dir in weeding_dirs:
        month = dir.split("/")[1]
        month_files = [file.name for file in os.scandir(dir) if file.is_file()]
        for filename in month_files:
            cursor.execute("SELECT 1 FROM posted_files WHERE name=?", (filename,))
            if cursor.fetchone() is None:
                print ("\t+ %s" % filename)
                file = parse_source_file(os.path.exists(os.path.join(dir, filename)))
                for initials in librarians:
                    if ("_%s_" % initials) in file["name"]:
                        cursor.execute(
                            "INSERT INTO posted_files (name, librarian_id, month) VALUES (?,?,?)",
                            (file["name"], file["cn_section"], librarians[initials]["id"], month)
                        )
                        file_id = cursor.lastrowid
                        break
                for book in file["books"]:
                    cursor.execute(
                        "INSERT INTO posted_books (barcode, file_id) VALUES (?,?)",
                        (int(book["barcode"]), file_id)
                    )
    conn.commit()

def addNewRequests():
    print ("Updating Faculty Requests...")
    cursor = conn.cursor()

    file = csv.reader(open("db_data/faculty_requests.csv", encoding="utf-8"))
    form_rows = []
    header = True
    for row in file:
        if header: # skip header
            header = False
            continue
        form_rows.append(row)
    # Sort by date
    form_rows.sort(key=lambda r: datetime.datetime.strptime(r[0], "%b %d, %Y, %I:%M:%S %p"))
    for row in form_rows:
        request = parse_request(row)
        # Get id
        cursor.execute("SELECT faculty_id FROM faculty WHERE name=? LIMIT 1", (request["faculty"]["name"],))
        faculty_id = cursor.fetchone()
        if faculty_id:
            faculty_id = faculty_id[0]
        else:
            faculty = request["faculty"]
            cursor.execute(
                "INSERT INTO faculty(name, department, address) VALUES (?,?,?);",
                (faculty["name"], faculty["department"], faculty["address"])
            )
            faculty_id = cursor.lastrowid
        # Check for old requests
        request_date = datetime.datetime.strptime(row[0], "%b %d, %Y, %I:%M:%S %p")
        cursor.execute("SELECT 1 FROM faculty_requests WHERE faculty_id=? AND date=?", (faculty_id, request_date))
        if cursor.fetchone() is None:
            cursor.execute(
                "INSERT INTO faculty_requests(faculty_id, date) VALUES (?,?);",
                (faculty_id, request_date)
            )
            request_id = cursor.lastrowid
            included_barcodes = []
            for book in request["books"]:
                if book["barcode"] in included_barcodes:
                    cursor.execute("""
                        SELECT posted_files.name FROM posted_files
                            INNER JOIN posted_books ON posted_books.file_id = posted_files.file_id
                            WHERE posted_books.barcode=?""", (book["barcode"],))
                    file_obj = cursor.fetchone()
                    print ("\tduplicate in this request: %s (%s)" % (book["barcode"], file_obj[0]))
                    continue
                cursor.execute(
                    "INSERT INTO faculty_books(barcode, personal, comment, request_id) VALUES (?,?,?,?);",
                    (book["barcode"], book["personal"], book["comment"], request_id)
                )
                included_barcodes.append(book["barcode"])
    conn.commit()

addNewPostedFile()
addNewRequests()

cursor = conn.cursor()
cursor.execute("""
    SELECT posted_files.cn_section, COUNT(posted_books.barcode) from posted_files
        INNER JOIN posted_books on posted_books.file_id = posted_files.file_id
        GROUP BY posted_files.cn_section""", ())
print (cursor.fetchall())

exit(0)

# TODO: CLean up

'''
# Make sure missing barcodes aren't just checked out
CHECKED_OUT_BARCODES = [str(int(x.strip())) for x in open("../checked_out/checkedout_since_greenglass.txt").read().split("\n")]
GG_CALLNUMBERS = open("../db_data/gg_callnumbers.txt", "r").read().split("\n")

# Load map of barcodes to callnumber sections
BARCODE_CN_MAP = json.load(open("../db_data/barcode_cn_map.json", "r"))
POSTED_CN_MAP = json.load(open("../db_data/posted_cn_map.json", "r"))
POSTED_COUNTS = {}
REVIEWED_COUNTS = {}


POSTED_BARCODES = []
weeding_dirs = [dir.path for dir in os.scandir("sources/") if dir.is_dir()]
print ("Updating Weeding Data...")
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
file = csv.reader(open("db_data/faculty_requests.csv", encoding="utf-8"))
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
'''