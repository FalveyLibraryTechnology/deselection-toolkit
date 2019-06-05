import csv
import datetime
import os
import sys

from typing import Iterable, Tuple
from sqlite3 import Connection, IntegrityError

from src.log_parsing import parse_request
from src.posted_files import parse_source_file
from src.utils import normalize_callnumber

csv.field_size_limit(sys.maxsize)


def queryFileCallnumberTopBottom(conn: Connection) -> Iterable[Tuple[str, str, str]]:
    cursor = conn.cursor()
    cursor.execute("SELECT cn_section, MIN(callnumber_sort), MAX(callnumber_sort)"
                   " FROM posted_books"
                   " GROUP BY cn_section")
    return cursor.fetchall()


def addNewPostedFiles(conn: Connection) -> None:
    print("\nUpdating Weeding Data...")

    cursor = conn.cursor()

    cursor.execute("SELECT initials, librarian_id FROM librarians")
    librarians = [{"initials": row[0], "id": row[1]} for row in cursor.fetchall()]

    weeding_dirs = [sub.path for sub in os.scandir("sources/") if sub.is_dir()]
    for subdir in weeding_dirs:
        month = subdir.split("/")[1]
        print("\t%s" % month)
        month_files = [file.name for file in os.scandir(subdir) if file.is_file()]
        for filename in month_files:
            cursor.execute("SELECT 1 FROM posted_files WHERE name=?", (filename,))
            if cursor.fetchone() is None:
                print("\t\t%s" % filename)
                file = parse_source_file(os.path.join(subdir, filename))
                file_id = -1
                for lib in librarians:
                    if ("_%s_" % lib["initials"]) in file["name"]:
                        month_date = datetime.datetime.strptime(month, "%Y %B")
                        cursor.execute(
                            "INSERT INTO posted_files (name, librarian_id, month) VALUES (?,?,?)",
                            (file["name"], lib["id"], month_date)
                        )
                        file_id = cursor.lastrowid
                        break
                for book in file["books"]:
                    try:
                        cursor.execute(
                            "INSERT INTO posted_books"
                            " (barcode, callnumber, callnumber_sort, cn_section, title, author, pub_year, file_id)"
                            " VALUES (?,?,?,?,?,?,?,?)",
                            (int(book["barcode"]), book["callnumber"], book["callnumber_sort"], book["cn_section"],
                             book["title"], book["author"], book["year"], file_id)
                        )
                    except IntegrityError as e:
                        if str(e)[0:6] != "UNIQUE":
                            print(e, book["barcode"])
                    except KeyError as e:
                        print("KeyError: %s" % e, book["callnumber"])
    conn.commit()


def addNewRequests(conn: Connection) -> None:
    print("\nUpdating Faculty Requests...")
    cursor = conn.cursor()

    # Set aside PR books for now
    valid_pr_set = set(open("db_data/pr_google_list.txt", newline="", encoding="utf-8").read().split("\n"))

    file = csv.reader(open("db_data/faculty_requests.csv", encoding="utf-8"))
    form_rows = []
    header = True
    prev_for_error = None
    for row in file:
        if header:  # skip header
            header = False
            continue
        try:
          datetime.datetime.strptime(row[0], "%b %d, %Y, %I:%M:%S %p")
        except:
          print("Invalid date")
          print(row)
          print("prev")
          print(prev_for_error)
          exit(1)
        form_rows.append(row)
        prev_for_error = row
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
        cursor.execute("SELECT request_id FROM faculty_requests WHERE faculty_id=? AND date=?",
                       (faculty_id, request["date"]))
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
            # Make sure book is a posted book
            cursor.execute("SELECT 1 FROM posted_books WHERE barcode=?", (book["barcode"],))
            if cursor.fetchone() is None:
                # Make sure this book isn't excluded
                cursor.execute("SELECT 1 FROM excluded_barcodes WHERE barcode=?", (book["barcode"],))
                if cursor.fetchone() is None and str(book["barcode"]) not in valid_pr_set:
                    print("\tinvalid barcode: %s (%s)" % (book["barcode"], request["date"]))
                continue
            # Duplicate barcode in same request
            if book["barcode"] in included_barcodes:
                cursor.execute("SELECT posted_files.name FROM posted_files"
                               " INNER JOIN posted_books ON posted_books.file_id = posted_files.file_id"
                               " WHERE posted_books.barcode=?", (book["barcode"],))
                file_obj = cursor.fetchone()
                print("\tduplicate in this request: %s (%s)" % (book["barcode"], file_obj[0] if file_obj else "n/a"))
                continue
            # Add new items
            cursor.execute("SELECT 1 FROM faculty_books WHERE barcode=? AND request_id=?", (book["barcode"], request_id))
            if cursor.fetchone() is None:
                cursor.execute(
                    "INSERT INTO faculty_books(barcode, personal, comment, request_id) VALUES (?,?,?,?);",
                    (book["barcode"], book["personal"], book["comment"], request_id)
                )
            included_barcodes.append(book["barcode"])
    conn.commit()


def updateReviewedCounts(conn: Connection) -> object:
    print("\nUpdating Reviewed Counts...")
    gg_callnumbers_norm = open("db_data/gg_callnumbers_norm.txt").read().split("\n")
    file_ranges = queryFileCallnumberTopBottom(conn)
    # Some items not recommended by gg are added to posted lists
    for range in file_ranges:
        section, top, bottom = range
        if not top in gg_callnumbers_norm:
            print ("\tadd top: %s" % top)
            gg_callnumbers_norm.append(top)
        if not bottom in gg_callnumbers_norm:
            print ("\tadd bottom: %s" % bottom)
            gg_callnumbers_norm.append(bottom)
    gg_callnumbers_norm.sort()
    # Distance between top and bottom indexes is number reviewed
    section_review_sums = {}
    for range in file_ranges:
        section, top, bottom = range
        review_min = gg_callnumbers_norm.index(top)
        review_max = gg_callnumbers_norm.index(bottom)
        if section in section_review_sums:
            section_review_sums[section] += review_max - review_min + 1  # inclusive
        else:
            section_review_sums[section] = review_max - review_min + 1
    cursor = conn.cursor()
    for section in section_review_sums:
        cursor.execute(
            "UPDATE callnumber_sections SET reviewed_count=? WHERE cn_section=?",
            (section_review_sums[section] if section in section_review_sums else 0, section)
        )
    conn.commit()
