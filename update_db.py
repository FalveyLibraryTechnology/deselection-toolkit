import csv
import json
import os
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

    cursor.execute("SELECT initials, librarian_id FROM librarians")
    librarians = [{ "initials": row[0], "id": row[1] } for row in cursor.fetchall()]

    weeding_dirs = [dir.path for dir in os.scandir("sources/") if dir.is_dir()]
    for dir in weeding_dirs:
        month = dir.split("/")[1]
        month_files = [file.name for file in os.scandir(dir) if file.is_file()]
        for filename in month_files:
            cursor.execute("SELECT 1 FROM posted_files WHERE name=?", (filename,))
            if cursor.fetchone() is None:
                print ("\t+ %s" % filename)
                file = parse_source_file(os.path.join(dir, filename))
                for lib in librarians:
                    if ("_%s_" % lib["initials"]) in file["name"]:
                        month_date = datetime.datetime.strptime(month, "%B %Y")
                        cursor.execute(
                            "INSERT INTO posted_files (name, cn_section, librarian_id, month) VALUES (?,?,?,?)",
                            (file["name"], file["cn_section"], lib["id"], month_date)
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
        cursor.execute("SELECT request_id FROM faculty_requests WHERE faculty_id=? AND date=?", (faculty_id, request["date"]))
        request_id = cursor.fetchone()
        if request_id:
            request_id = request_id[0]
        else:
            cursor.execute(
                "INSERT INTO faculty_requests(faculty_id, date) VALUES (?,?);",
                (faculty_id, request["date"])
            )
            request_id = cursor.lastrowid
        included_barcodes = []
        for book in request["books"]:
            # Duplicate barcode in same request
            if book["barcode"] in included_barcodes:
                cursor.execute("""
                    SELECT posted_files.name FROM posted_files
                        INNER JOIN posted_books ON posted_books.file_id = posted_files.file_id
                        WHERE posted_books.barcode=?""", (book["barcode"],))
                file_obj = cursor.fetchone()
                print ("\tduplicate in this request: %s (%s)" % (book["barcode"], file_obj[0]))
                continue
            # Make sure book is a posted book
            cursor.execute("SELECT 1 FROM posted_books WHERE barcode=?", (book["barcode"], ))
            if cursor.fetchone() is None:
                print ("\tinvalid barcode: %s (%s)" % (book["barcode"], request["date"]))
                continue
            # Add new items
            cursor.execute("SELECT 1 FROM faculty_books WHERE barcode=?", (book["barcode"], ))
            if cursor.fetchone() is None:
                cursor.execute(
                    "INSERT INTO faculty_books(barcode, personal, comment, request_id) VALUES (?,?,?,?);",
                    (book["barcode"], book["personal"], book["comment"], request_id)
                )
            included_barcodes.append(book["barcode"])
    conn.commit()

def queryFileCallnumberTopBottom():
    cursor = conn.cursor()
    cursor.execute("""
        SELECT posted_files.cn_section, MIN(posted_books.callnumber_sort), MAX(posted_books.callnumber_sort)
            FROM posted_books
            INNER JOIN posted_files ON posted_files.file_id = posted_books.file_id
            GROUP BY posted_files.file_id""")
    return cursor.fetchall()

def updateReviewedCounts():
    print ("Updating Reviewed Counts...")
    gg_callnumbers_norm = open("db_data/gg_callnumbers_norm.txt").read().split("\n")
    file_ranges = queryFileCallnumberTopBottom()
    # Some items not recommended by gg are added to posted lists
    for range in file_ranges:
        section, top, bottom = range
        if not top in gg_callnumbers_norm:
            gg_callnumbers_norm.append(top)
        if not bottom in gg_callnumbers_norm:
            gg_callnumbers_norm.append(bottom)
    gg_callnumbers_norm.sort()
    # Distance between top and bottom indexes is number reviewed
    section_review_sums = {}
    for range in file_ranges:
        section, top, bottom = range
        review_min = gg_callnumbers_norm.index(top)
        review_max = gg_callnumbers_norm.index(bottom)
        if section in section_review_sums:
            section_review_sums[section] += review_max - review_min + 1 # inclusive
        else:
            section_review_sums[section] = review_max - review_min + 1
    cursor = conn.cursor()
    for section in section_review_sums:
        cursor.execute(
            "UPDATE callnumber_sections SET reviewed_count=? WHERE cn_section=?",
            (section_review_sums[section], section)
        )

addNewPostedFile()
addNewRequests()
updateReviewedCounts()

# Callnumbers reviewed
# c = conn.cursor()
# for section in POSTED_COUNTS:
#     c.execute("UPDATE callnumbers SET posted_count=? WHERE section=?", (POSTED_COUNTS[section], section))
# for section in REVIEWED_COUNTS:
#     c.execute("UPDATE callnumbers SET reviewed_count=? WHERE section=?", (REVIEWED_COUNTS[section], section))
