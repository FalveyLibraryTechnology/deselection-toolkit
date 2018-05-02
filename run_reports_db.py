import csv
import datetime
import json
import os
import re
import sys
import sqlite3

conn = sqlite3.connect("database.sqlite")
cursor = conn.cursor()

def writeCSVFile(filename, month, columns, data):
    with open("db_reports/%s/%s" % (month, filename), "w", newline="", encoding="utf8") as outfile:
        writer = csv.writer(outfile)
        writer.writerow(columns)
        writer.writerows(data)

def queryForAllFacultyRequests(month_date):
    cursor.execute("""
        SELECT posted_books.barcode, posted_books.callnumber, posted_books.title, posted_books.author, posted_books.pub_year, faculty.name, faculty_books.personal, faculty_requests.date
            FROM posted_books
            INNER JOIN faculty_books ON faculty_books.barcode = posted_books.barcode
            INNER JOIN faculty_requests ON faculty_requests.request_id = faculty_books.request_id
            INNER JOIN faculty ON faculty.faculty_id = faculty_requests.faculty_id
            INNER JOIN posted_files ON posted_files.file_id = posted_books.file_id
            WHERE posted_files.month = ?
            ORDER BY faculty_books.barcode ASC, faculty_requests.date ASC""", (month_date, ))
    return cursor.fetchall()

def queryForAllFacultyEffective(month_date):
    cursor.execute("""
        SELECT posted_books.barcode, posted_books.callnumber, posted_books.title, posted_books.author, posted_books.pub_year, faculty.name, faculty_books.personal
            FROM posted_books
            INNER JOIN faculty_books ON faculty_books.barcode = posted_books.barcode
            INNER JOIN faculty_requests ON faculty_requests.request_id = faculty_books.request_id
            INNER JOIN faculty ON faculty.faculty_id = faculty_requests.faculty_id
            INNER JOIN posted_files ON posted_files.file_id = posted_books.file_id
            WHERE posted_files.month = ?
            GROUP BY faculty_books.barcode
            ORDER BY faculty_books.barcode ASC, faculty_books.personal ASC, faculty_requests.date ASC""", (month_date, ))
    return cursor.fetchall()

def queryForPersonalEffective(month_date):
    cursor.execute("""
        SELECT posted_books.callnumber, faculty.name, faculty.address, posted_books.title, posted_books.author, posted_books.pub_year, posted_books.barcode
            FROM posted_books
            INNER JOIN faculty_books ON faculty_books.barcode = posted_books.barcode
            INNER JOIN faculty_requests ON faculty_requests.request_id = faculty_books.request_id
            INNER JOIN faculty ON faculty.faculty_id = faculty_requests.faculty_id
            INNER JOIN posted_files ON posted_files.file_id = posted_books.file_id
            WHERE posted_files.month = ?
                AND NOT EXISTS(SELECT 1 FROM faculty_books WHERE personal = 0 AND barcode = posted_books.barcode)
            GROUP BY faculty_books.barcode
            ORDER BY posted_books.callnumber_sort ASC, faculty_requests.date ASC""", (month_date, ))
    return cursor.fetchall()

def queryForMasterList(month_date):
    cursor.execute("""
        SELECT posted_books.callnumber, posted_books.title, posted_books.author, posted_books.pub_year, posted_books.barcode
            FROM posted_books
            INNER JOIN posted_files ON posted_files.file_id = posted_books.file_id
            WHERE posted_files.month = ?
                AND NOT EXISTS(SELECT 1 FROM faculty_books WHERE barcode = posted_books.barcode)
            ORDER BY posted_books.callnumber_sort ASC""", (month_date, ))
    return cursor.fetchall()

months = [dir.path.split("/")[1] for dir in os.scandir("sources/") if dir.is_dir()]
for month in months:
    print ("\t%s" % month)
    month_date = datetime.datetime.strptime(month, "%B %Y")
    if not os.path.exists("db_reports/%s/" % month):
        os.mkdir("db_reports/%s/" % month)
    # Faculty All Requests
    writeCSVFile(
        "faculty-all-requests.csv", month,
        ["Barcode", "Callnumber", "Title", "Author", "Publish Year", "Faculty Name", "Personal", "Request Date"],
        queryForAllFacultyRequests(month_date)
    )
    # Faculty Effective
    writeCSVFile(
        "faculty-effective-requests.csv", month,
        ["Barcode", "Callnumber", "Title", "Author", "Publish Year", "Faculty Name", "Personal"],
        queryForAllFacultyEffective(month_date)
    )
    # Personal Retention Effective
    writeCSVFile(
        "faculty-requests-for-personal-collections.csv", month,
        ["Callnumber", "Faculty Name", "Faculty Address", "Title", "Author", "Publish Year", "Barcode"],
        queryForPersonalEffective(month_date)
    )
    # Master Pull List
    writeCSVFile(
        "master-pull-list.csv", month,
        ["Callnumber", "Title", "Author", "Publish Year", "Barcode"],
        queryForMasterList(month_date)
    )

exit(0)

from checksumdir import dirhash # folder md5
from xlrd import open_workbook  # Excel files

from ProgressBar import ProgressBar

csv.field_size_limit(sys.maxsize)

# Barcodes removed for being checked out
CHECKED_OUT_BARCODES = [str(int(x.strip())) for x in open("checked_out/checkedout_since_greenglass.txt").read().split("\n")]

DEBUG = "no thanks" # choose a barcode to check

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

# print (normalize_callnumber("BL237.5.Q47 1988") )
# BL 0237500Q  47          1988
# print (normalize_callnumber("BL237 .I5")        )
# BL 0237000I  5
# print (normalize_callnumber("D308.A442")        )
# D  0308000A  442

def make_unique(arr):
    return list(set(filter(None, arr)))

REVIEWED_COUNT = 0
def parse_crtf_dir(reports_dir):
    global LIBRARIAN_RETENTION, REVIEWED_COUNT

    month_data = {}
    hash = dirhash(reports_dir, 'md5')
    if not os.path.exists('hashes/'):
        os.mkdir('hashes/')
    if True or not os.path.exists('hashes/%s.json' % hash):
        for dirpath, dirnames, filenames in os.walk(reports_dir):
            for filename in filenames:
                with open_workbook(os.path.join(dirpath, filename)) as book:
                    sheet = book.sheet_by_index(0)
                    rvalues = sheet.row_values(0)
                    column_names = [
                        "Display Call Number",
                        "Barcode",
                        "Title",
                        "Author",
                        "Publication Year",
                    ]
                    columns = []
                    auto = True
                    for name in column_names:
                        if name in rvalues:
                            columns.append(rvalues.index(name))
                        else:
                            auto = False
                            break
                    print ("\t\t%s:" % filename)
                    if not auto:
                        for i in range(len(rvalues)):
                            print ("\t%d: %s" % (i, rvalues[i]))
                        columns = [int(x) for x in input("\nWhich cols correspond to %s?\n(comma separated) >: " % ", ".join(column_names)).split(',')]
                        print ([rvalues[x] for x in columns])
                        print ("\n")
                    # else:
                    #     print ("\t\t\tAuto-detected columns: %s" % ", ".join([str(x) for x in columns]))

                    check_letter = filename[0]
                    callnumbers = []
                    for row in range(1, sheet.nrows):
                        rvalues = sheet.row_values(row)
                        barcode = str(rvalues[columns[1]]).split(".")[0] # Remove decimaled barcodes
                        if barcode == DEBUG:
                            print ("DEBUG - parse_crtf_dir")
                        month_data[barcode] = {
                            "callnumber": rvalues[columns[0]],
                            "barcode": barcode,
                            "year": str(rvalues[columns[4]]).split(".")[0],
                            "title": rvalues[columns[2]],
                            "author": rvalues[columns[3]],
                            "callnumber_sort": normalize_callnumber(rvalues[columns[0]]),
                        }
                        callnumbers.append(month_data[barcode]["callnumber_sort"])
                    # Calculate library retention
                    callnumbers.sort()
                    REVIEWED_COUNT += len(callnumbers)
                    first_callnumber = False
                    last_callnumber = False
                    for i in range(0, 20):
                        if check_letter == callnumbers[i][0]:
                            first_callnumber = callnumbers[i]
                            break
                    for i in range(0, 20):
                        index = len(callnumbers) - i - 1
                        if check_letter == callnumbers[index][0]:
                            last_callnumber = callnumbers[index]
                            break
                    first_index = GG_CALLNUMBERS.index(first_callnumber)
                    last_index = GG_CALLNUMBERS.index(last_callnumber)
                    gg_rec = last_index - first_index + 1
                    LIBRARIAN_RETENTION += gg_rec - len(callnumbers)
                    print ("\t\t\tLibrarian Retention: %d (%d - %d)" % (gg_rec - len(callnumbers), gg_rec, len(callnumbers)))
                    print ("\t\t\t\t%d %s" % (first_index, first_callnumber))
                    print ("\t\t\t\t%d %s" % (last_index, last_callnumber))
        with open('hashes/%s.json' % hash, 'w') as jsonFile:
            json.dump(month_data, jsonFile, separators=(',',':'))
    else:
        with open('hashes/%s.json' % hash) as jsonFile:
            month_data = json.load(jsonFile)
    return month_data

all_faculty = {}        # Faculty data
all_requests_by_month = {} # All book requests with data
all_effective = {}      # Full book data
def parse_form(row, month):
    global all_retained_books, all_faculty, effective_by_month, effective_personal, effective_retained

    log_barcodes = [] # Barcodes
    all_requests = [] # Request data

    date = row[0]
    form = row[4]
    lines = form.split('\n')
    current = 0
    faculty = {}
    while lines[current] != 'Faculty First Name:':
        current += 1
    faculty['name'] = lines[current + 1]

    while lines[current] != 'Faculty Last Name:':
        current += 1
    faculty['name'] += ' ' + lines[current + 1]

    while lines[current] != 'Faculty Department:':
        current += 1
    faculty['department'] = lines[current + 1]

    while lines[current] != 'Campus Address:':
        current += 1
    faculty['address'] = lines[current + 1]

    if faculty["name"] in all_faculty:
        # Update address
        if len(faculty["address"]) > len(all_faculty[faculty["name"]]["address"]):
            all_faculty[faculty["name"]]["address"] = faculty["address"]
        # Update department
        if len(faculty["department"]) > len(all_faculty[faculty["name"]]["department"]):
            all_faculty[faculty["name"]]["department"] = faculty["department"]
    else:
        all_faculty[faculty["name"]] = faculty

    book_submissions = form.split('Barcode:\n')[1:]
    for bt in book_submissions:
        bc = 0
        blines = bt.split('\n')
        barcode = blines[0].strip()
        if barcode == DEBUG:
            print ("DEBUG - parse_form")

        if not barcode in weeding_data_books:
            if barcode == DEBUG:
                print ("DEBUG - not in weeding_data_books")
            if not barcode in CHECKED_OUT_BARCODES:
                print ("\t\tmissing barcode: %s (%s, %s)" % (barcode, faculty["name"], faculty["department"]))
            continue
        log_barcodes.append(barcode)

        book = {
            "date": date,
            "faculty": faculty["name"],
            "month": month,
        }

        while blines[bc] != 'Destination:':
            # print (bc, len(blines), blines[bc])
            bc += 1
        book["for_personal"] = blines[bc + 1].strip() == 'Patron'

        while blines[bc] != 'Comment:':
            bc += 1
        book['comment'] = '\n'.join(blines[bc + 1:]).strip()

        all_requests.append(book)

        book.update(weeding_data_books[barcode])

        # Check if book already retained for collection
        if not barcode in all_effective:
            all_effective[barcode] = book
        elif not book["for_personal"]:
            all_effective[barcode]["for_personal"] = False

    return [log_barcodes, all_requests]

def book_to_row_headers():
    return "Callnumber,Barcode,Publication Year,Title,Author"
def book_to_row(book):
    return '"%s",%s,%s,"%s","%s"' % (
        book["callnumber"],
        book["barcode"],
        book["year"],
        book["title"],
        book["author"],
    )

def create_retention_by_callnumber(books, month):
    books.sort(key=lambda b: b["callnumber_sort"])
    with open('reports/%s/all-retention-by-callnumber.csv' % month, 'w', encoding="utf8") as outfile:
        outfile.write('%s,Destination,Requesting Faculty,Comment\n' % book_to_row_headers())
        for record in books:
            outfile.write('%s,"%s","%s","%s"\n' % (book_to_row(record), "Personal" if record["for_personal"] else "Retain", record["faculty"], record["comment"]))

def create_retention_by_faculty(books, month):
    last_name = ""
    books.sort(key=lambda b: b["faculty"])
    with open('reports/%s/all-retention-by-faculty.csv' % month, 'w', encoding="utf8") as outfile:
        outfile.write("Faculty,Department,Address\n")
        outfile.write(",Retention Type,%s,Comment\n" % book_to_row_headers())
        for record in books:
            if last_name != record["faculty"]:
                last_name = record["faculty"]
                faculty = all_faculty[record["faculty"]]
                outfile.write('"%s","%s","%s"\n' % (faculty["name"], faculty["department"], faculty["address"]))
            outfile.write(',"%s",%s,"%s"\n' % ("Personal" if record["for_personal"] else "Retain", book_to_row(record), record["comment"]))

def create_personal_by_callnumber(books, month):
    personal = [b for b in books if b["for_personal"]]
    books.sort(key=lambda b: b["callnumber_sort"])
    with open('reports/%s/for-personal-collections-by-callnumber.csv' % month, 'w', encoding="utf8") as outfile:
        outfile.write('%s,Requesting Faculty,Campus Address\n' % book_to_row_headers())
        for record in personal:
            outfile.write('%s,"%s","%s","%s"\n' % (book_to_row(record), record["faculty"], all_faculty[record["faculty"]]["address"], record["comment"]))

def create_personal_by_faculty(books, month):
    last_name = ""
    personal = [b for b in books if b["for_personal"]]
    personal.sort(key=lambda b: b["faculty"])
    with open('reports/%s/for-personal-collections-by-faculty.csv' % month, 'w', encoding="utf8") as outfile:
        outfile.write("Faculty,Department,Address\n")
        outfile.write(",%s,Comment\n" % book_to_row_headers())
        for record in personal:
            if last_name != record["faculty"]:
                last_name = record["faculty"]
                faculty = all_faculty[record["faculty"]]
                outfile.write('"%s","%s","%s"\n' % (faculty["name"], faculty["department"], faculty["address"]))
            outfile.write(',%s,"%s"\n' % (book_to_row(record), record["comment"]))

faculty_email_map = {}
class_json = json.load(open("class_data.json", "r"))
for c in class_json:
    faculty_email_map[c["prof_name"]] = c["prof_email"]
def create_emails(books, month):
    global all_faculty, all_requests_by_month
    faculty_emails = {}
    for request in all_requests_by_month[month]:
        if request["barcode"] in all_effective and request["for_personal"]:
            if not request["faculty"] in faculty_emails:
                faculty_emails[request["faculty"]] = {
                    "theirs": [],
                    "in_library": [],
                    "too_late": [],
                }
            record = all_effective[request["barcode"]]
            if record["barcode"] == request["barcode"]:
                if record["for_personal"]:
                    if record["faculty"] == request["faculty"]:
                        faculty_emails[request["faculty"]]["theirs"].append(record["title"])
                    else:
                        faculty_emails[request["faculty"]]["too_late"].append(record["title"])
                else:
                    faculty_emails[request["faculty"]]["in_library"].append(record["title"])

    with open('reports/%s/personal-retention-emails.csv' % month, 'w', newline="", encoding="utf8") as outfile:
        writer = csv.writer(outfile)
        writer.writerow(["Faculty", "Department", "Address", "Email Address", "Email Text"])
        for name in faculty_emails:
            faculty = faculty_emails[name]
            name_regex = re.compile(" .*?".join(name.split(" ")))
            email_address = ""
            for prof in faculty_email_map:
                if name_regex.match(prof):
                    email_address = faculty_email_map[prof]
                    break
            if not email_address:
                print ("\t\tNo email for %s" % name)
            # print (name, len(faculty["theirs"]))
            if len(faculty["in_library"]) + len(faculty["theirs"]) + len(faculty["too_late"]) == 0:
                continue
            receiving = ""
            if len(faculty["theirs"]) > 0:
                receiving = "You will be receiving the following books:\n\n - %s" % "\n - ".join(make_unique(faculty["theirs"]))
            else:
                receiving = "Unfortunately, all of the books you requested fell into one of these precedence categories."
            staying = ""
            if False and len(faculty["in_library"]) > 0:
                staying = "\n\nThe following books you requested will be kept in the collection:\n\n - %s" % "\n - ".join(make_unique(faculty["in_library"]))
            other = ""
            if False and len(faculty["too_late"]) > 0:
                if len(faculty["theirs"]) > 0 or len(faculty["in_library"]) > 0:
                    if len(faculty["too_late"]) == 1:
                        other = "\n\nThe final book you requested was requested by another faculty member before you, so you will not be receiving this item."
                    else:
                        other = "\n\nThe remaining %d books you requested were requested by another faculty member before you requested them, so you will not be receiving those items." % len(faculty["too_late"])
                else:
                    if len(faculty["too_late"]) == 1:
                        other = "\n\nUnfortunately, the book you requested was requested by another faculty member before you, so we're sorry to say that you will not be receiving your requested item."
                    else:
                        other = "\n\nUnfortunately, all the books you requested were requested by another faculty member before you requested them, so we're sorry to say that you will not be receiving your requested items."
            writer.writerow([name, all_faculty[name]["department"], all_faculty[name]["address"], email_address,
"""Dear %s,

We received your request to keep some of the deselected books for your own collection. This email is to inform you of the outcome of that request. We take a few things into consideration when we handle personal requests and these considerations may affect which of your requested items you receive. First, if anyone requested a book to stay in the library's collection, that will take precedence over a personal request. Also, personal requests are on a first-come, first-serve basis, so if someone requested one of the books you wanted before you did, the earlier request will take precedence.

%s%s%s

Please contact me with questions or concerns via email at cordesia.pope@villanova.edu.

Thank you,

Cordesia Pope
Collection Review Task Force
Falvey Memorial Library
""" % (name, receiving, staying, other)])

def create_master_list(month_barcodes, month):
    global weeding_data_books, weeding_data_by_month

    master_barcodes = weeding_data_by_month[month][:]

    for barcode in month_barcodes:
        if barcode in master_barcodes:
            master_barcodes.remove(barcode)
        else:
            print ("\t\tWrong month?: %s" % barcode)
    print ("\t\t%s master list: %d - %d = %d === %d" % (
        month,
        len(weeding_data_by_month[month]),
        len(month_barcodes),
        len(weeding_data_by_month[month]) - len(month_barcodes),
        len(master_barcodes),
    ))

    # Check logs for barcodes
    log_file = "sources/%s-log.csv" % month
    log_file_text = ""
    if os.path.exists(log_file):
        print ("\t\tChecking against %s..." % log_file)
        log_file_text = open(log_file, "r", encoding="utf-8").read()
    else:
        print ("\t\tChecking against all logs...")
        log_files = [file.name for file in os.scandir("sources/") if file.is_file()]
        for log in log_files:
            log_file_text += open("sources/%s" % log).read()
    if len(log_file_text) > 0:
        for barcode in master_barcodes:
            if barcode in log_file_text:
                print("\t\tERROR: %s" % barcode)
                master_barcodes.remove(barcode)

    master_list = [weeding_data_books[b] for b in master_barcodes]
    master_list.sort(key=lambda b: b["callnumber_sort"])
    with open('reports/%s/master-pull-list.csv' % month, 'w', encoding="utf8") as outfile:
        outfile.write('%s,"Action Taken"\n' % book_to_row_headers())
        for b in master_list:
            outfile.write('%s,\n' % book_to_row(b))

# Compile all resources into weeding_master
weeding_data_books = {}
weeding_data_by_month = {}
weeding_dirs = [dir.path for dir in os.scandir("sources/") if dir.is_dir()]
print ("Gathering All Weeding Data...")
file_ranges = {}
LIBRARIAN_RETENTION = 0
GG_CALLNUMBERS = open("gg_archive/gg_callnumbers.txt", "r").read().split("\n")
for dir in weeding_dirs:
    month = dir.split("/")[1]
    print ("\t%s" % month)
    month_data = parse_crtf_dir(dir)
    weeding_data_books.update(month_data)
    weeding_data_by_month[month] = make_unique(month_data.copy().keys())

print ("Analyzing Monthly Log Files...")
log_files = [file.name for file in os.scandir("sources/") if file.is_file()]
for log in log_files:
    month = log.split("-")[0]
    month_barcodes = []
    all_requests_by_month[month] = []
    print ("\t%s" % month)

    file = csv.reader(open("sources/%s" % log, "r", encoding="utf-8"))
    form_rows = []
    header = True
    for row in file:
        if header:
            header = False
            continue
        form_rows.append(row)
    form_rows.sort(key=lambda r: datetime.datetime.strptime(r[0], "%b %d, %Y, %I:%M:%S %p"))
    for row in form_rows:
        barcodes, requests = parse_form(row, month)
        month_barcodes.extend(barcodes)
        all_requests_by_month[month].extend(requests)
    month_barcodes = make_unique(month_barcodes)

    month_books = []
    for barcode in month_barcodes:
        month_books.append(dict(all_effective[barcode]))

    if not os.path.exists('reports/%s' % month):
        os.mkdir('reports/%s' % month)
    create_retention_by_callnumber(month_books, month)
    create_retention_by_faculty(month_books, month)
    create_personal_by_callnumber(month_books, month)
    create_personal_by_faculty(month_books, month)
    create_emails(month_books, month)
    # Master list
    create_master_list(month_barcodes, month)
    # Graphs
    create_department_graph(weeding_data_by_month[month], month_books, month)
    create_faculty_graph(month_books, month)

# Cumulative Records
print ("\nGenerating cumulative reports...")
cumulative_folder = "Cumulative"
if not os.path.exists('reports/%s' % cumulative_folder):
    os.mkdir('reports/%s' % cumulative_folder)

all_retained_books = []
for barcode in all_effective:
    all_retained_books.append(all_effective[barcode])
# Reports
create_retention_by_callnumber(all_retained_books, cumulative_folder)
create_retention_by_faculty(all_retained_books, cumulative_folder)
create_personal_by_callnumber(all_retained_books, cumulative_folder)
create_personal_by_faculty(all_retained_books, cumulative_folder)
# Graphs
create_department_graph(weeding_data_books.copy().keys(), all_retained_books, cumulative_folder)
create_faculty_graph(all_retained_books, cumulative_folder)

print ("\nGenerating callnumber breakdowns...")
totals = callnumber_breakdowns(cumulative_folder)

print ("\nExport all retention as json...")
all_book_requests = []
for month in all_requests_by_month:
    all_book_requests.extend(all_requests_by_month[month])

owner = {}
all_book_requests.sort(key=lambda x: datetime.datetime.strptime(x["date"], "%b %d, %Y, %I:%M:%S %p"))
for i in range(len(all_book_requests)):
    book = all_book_requests[i]
    if not book["barcode"] in owner:
        owner[book["barcode"]] = i
        continue
    curr = owner[book["barcode"]]
    if not book["for_personal"] and all_book_requests[curr]["for_personal"]:
        owner[book["barcode"]] = i
for i in range(len(all_book_requests)):
    book = all_book_requests[i]
    book["overridden"] = owner[book["barcode"]] != i

all_book_requests.sort(key=lambda x: x["barcode"])
for book in all_book_requests:
    if book["barcode"] in weeding_data_books:
        book.update(weeding_data_books[book["barcode"]])
        book["department"] = all_faculty[book["faculty"]]["department"]
        del book["faculty"]

if "totals" in globals():
    totals.update({ "retention": all_book_requests })
    json.dump(totals, open("retention_data.json", "w"), indent=4, sort_keys=True)

COLLECTION_COUNT = 541277 # GG XLSX
REVIEWED_COUNT += LIBRARIAN_RETENTION
FACULTY_PROTECTED = len([b for b in all_effective if not all_effective[b]["for_personal"]])
FACULTY_KEPT = len([b for b in all_effective if all_effective[b]["for_personal"]])
REMOVED = REVIEWED_COUNT - LIBRARIAN_RETENTION - FACULTY_PROTECTED
with open("progress_report.tsv", "w") as report:
    report.write("Category\tTotal\tPercentage of Total\tPercentage of GG Recommendations\tPercentage of Reviewed\tPercentage of Items Posted for Faculty Review\n")
    report.write("All Monographs\t%s\n" % (comma(COLLECTION_COUNT),))
    report.write(
        "Protected by GreenGlass Criteria\t%s\t%0.1f%%\n" % (
            comma(COLLECTION_COUNT - len(GG_CALLNUMBERS)),
            100 * (COLLECTION_COUNT - len(GG_CALLNUMBERS)) / COLLECTION_COUNT
        )
    )
    report.write(
        "Reviewed To Date\t%s\t%0.2f%%\t%0.2f%%\n" % (
            comma(REVIEWED_COUNT),
            100 * REVIEWED_COUNT / COLLECTION_COUNT,
            100 * REVIEWED_COUNT / len(GG_CALLNUMBERS),
        )
    )
    report.write(
        "Protected by Librarians\t%s\t%0.2f%%\t%0.2f%%\t%0.2f%%\n" % (
            comma(LIBRARIAN_RETENTION),
            100 * LIBRARIAN_RETENTION / COLLECTION_COUNT,
            100 * LIBRARIAN_RETENTION / len(GG_CALLNUMBERS),
            100 * LIBRARIAN_RETENTION / REVIEWED_COUNT,
        )
    )
    report.write(
        "Protected by Faculty\t%s\t%0.2f%%\t%0.2f%%\t%0.2f%%\t%0.2f%%\n" % (
            comma(FACULTY_PROTECTED),
            100 * FACULTY_PROTECTED / COLLECTION_COUNT,
            100 * FACULTY_PROTECTED / len(GG_CALLNUMBERS),
            100 * FACULTY_PROTECTED / REVIEWED_COUNT,
            100 * FACULTY_PROTECTED / (REVIEWED_COUNT - LIBRARIAN_RETENTION),
        )
    )
    report.write(
        "Kept by Faculty\t%s\t%0.2f%%\t%0.2f%%\t%0.2f%%\t%0.2f%%\n" % (
            comma(FACULTY_KEPT),
            100 * FACULTY_KEPT / COLLECTION_COUNT,
            100 * FACULTY_KEPT / len(GG_CALLNUMBERS),
            100 * FACULTY_KEPT / REVIEWED_COUNT,
            100 * FACULTY_KEPT / (REVIEWED_COUNT - LIBRARIAN_RETENTION),
        )
    )
    report.write(
        "Removed from the Library (Donated or Kept)\t%s\t%0.2f%%\t%0.2f%%\t%0.2f%%\n" % (
            comma(REMOVED),
            100 * REMOVED / COLLECTION_COUNT,
            100 * REMOVED / len(GG_CALLNUMBERS),
            100 * REMOVED / REVIEWED_COUNT,
        )
    )
