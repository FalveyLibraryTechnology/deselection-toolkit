import csv
import datetime
import json
import os
import re
import sys

from checksumdir import dirhash # folder md5
from xlrd import open_workbook  # Excel files

from graphs import bar_graph, box_chart, pie_chart
from ProgressBar import ProgressBar

csv.field_size_limit(sys.maxsize)

# Barcodes removed for being checked out
CHECKED_OUT_BARCODES = [str(int(x.strip())) for x in open("checked_out/barcodes_since_01Apr2017.txt").read().split("\n")]

DEBUG = "no thanks"

def comma(num):
    return '{:,}'.format(num)
def normalize_callnumber(callnumber):
    # BL237.5.Q47 1988
    # BL237 .I5
    # BL 0237000I  5
    # BV 1471200T  8           1990
    # BV 2160000               1908
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
    return ("%s %04d00%s  %s" % (section.ljust(2), float(number) * 10, letter, extra)).strip()

# print (normalize_callnumber("BL237.5.Q47 1988") )
# BL 0237500Q  47          1988
# print (normalize_callnumber("BL237 .I5")        )
# BL 0237000I  5
# print (normalize_callnumber("D308.A442")        )
# D  0308000A  442

def make_unique(arr):
    return list(set(filter(None, arr)))

def parse_crtf_dir(reports_dir):
    month_data = {}
    hash = dirhash(reports_dir, 'md5')
    if not os.path.exists('hashes/'):
        os.mkdir('hashes/')
    if not os.path.exists('hashes/%s.json' % hash):
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
                    else:
                        print ("\t\t\tAuto-detected columns: %s" % ", ".join([str(x) for x in columns]))

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

def label_graph(filename, department_bars, month):
    department_labels = []
    for bar in department_bars:
        name = bar[3]
        p1 = 100 * bar[1] / bar[0]
        p2 = 100 * bar[2] / bar[0]
        label = name
        if p1 > 0 or p2 > 0:
            label += "\n"
        if p1 > 0:
            label += "%.1f%%" % p1
            if p2 > 0:
                label += "/"
        if p2 > 0:
            label += "%.1f%%" % p2
        department_labels.append(label)
    bar_graph(
        "reports/%s/%s.png" % (month, filename),
        [bar[:3] for bar in department_bars],
        key=["Total Marked", "Total Retained", "Retained for Personal"],
        labels=department_labels,
        title=month
    )

def create_department_graph(weeding_barcodes, books, month):
    department_counts = {}
    for barcode in weeding_barcodes:
        dept_match = re.search('^([A-Z]+)', weeding_data_books[barcode]["callnumber"])
        department = dept_match.group(1)
        if not department in department_counts:
            department_counts[department] = {
                "name": department,
                "total": 0,
                "retain": 0,
                "personal": 0,
            }
        department_counts[department]["total"] += 1

    for record in books:
        dept_match = re.search('^([A-Z]+)', record["callnumber"])
        department = dept_match.group(1)
        if not department in department_counts:
            print ("Wrong Month: %s (%s)" % (record["barcode"], department))
        else:
            department_counts[department]["retain"] += 1
            if record["for_personal"]:
                department_counts[department]["personal"] += 1

    department_bars = []
    for department in department_counts:
        department_bars.append([
            department_counts[department]["total"],
            department_counts[department]["retain"],
            department_counts[department]["personal"],
            department_counts[department]["name"],
        ])

    department_bars.sort(key=lambda x: x[3], reverse=False)
    label_graph("callnumber_areas_by_callnumber", department_bars, month)

    department_bars.sort(key=lambda x: x[0], reverse=True)
    label_graph("callnumber_areas_by_size", department_bars, month)

    department_bars.sort(key=lambda x: x[1], reverse=True)
    label_graph("callnumber_areas_by_retention", department_bars, month)

    # department_bars.sort(key=lambda x: x[1] / x[0], reverse=True)
    # label_graph("callnumber_areas_by_retention_percent", department_bars, month)

def create_faculty_graph(books, month):
    books.sort(key=lambda b: b["faculty"])

    faculty = {}
    for record in books:
        if not record["faculty"] in faculty:
            faculty[record["faculty"]] = {
                "total": 0,
                "personal": 0,
            }
        faculty[record["faculty"]]["total"] += 1
        if record["for_personal"]:
            faculty[record["faculty"]]["personal"] += 1

    sorted_faculty = []
    for name in faculty:
        sorted_faculty.append({
            "name": all_faculty[name]["name"],
            "department": all_faculty[name]["department"],
            "books": faculty[name]["total"],
            "personal": faculty[name]["personal"],
        })
    sorted_faculty.sort(key=lambda f: f["books"], reverse=True)

    faculty_bars = []
    faculty_labels = []
    for f in sorted_faculty:
        faculty_labels.append("%s\n%s" % (f["name"].replace(" ", " \n"), f["department"].split(" ")[0]))
        faculty_bars.append([
            f["books"],
            f["personal"],
        ])
    bar_graph(
        "reports/%s/faculty.png" % month, faculty_bars,
        key=["Total Retained", "Retained for Personal"],
        labels=faculty_labels,
        title=month
    )

def callnumber_breakdowns(folder):
    global all_effective

    department_counts = {}
    for barcode in all_effective:
        dept_match = re.search('^([A-Z]+)', weeding_data_books[barcode]["callnumber"])
        department = dept_match.group(1)
        if not department in department_counts:
            department_counts[department] = {
                "name": department,
                "total": 0,
                "retain": 0,
                "personal": 0,
            }
        department_counts[department]["total"] += 1
        record = all_effective[barcode]
        department_counts[department]["total"] += 1
        if record["for_personal"]:
            department_counts[department]["personal"] += 1
        else:
            department_counts[department]["retain"] += 1

    gg_recommendations = {}
    collection_totals = {}
    with open_workbook("GreenGlass Project Overview.xlsx") as gg_report:
        sheet = gg_report.sheet_by_index(0)
        for r in range(2, sheet.nrows):
            rvalues = [str(x).strip() for x in sheet.row_values(r)]
            if len(rvalues) < 7 or len(rvalues[0]) == 0:
                continue
            callnumber = rvalues[0]
            if callnumber[:11] == "Exception: ":
                callnumber = callnumber[11:]
            if len(callnumber) > 2:
                callnumber = callnumber[:2]
            gg_withdrawl = int(float(rvalues[6])) if len(rvalues[6]) > 0 else 0 # Matches
            c_total = int(float(rvalues[5])) if len(rvalues[5]) > 0 else 0      # Total
            if callnumber in department_counts:
                if not callnumber in gg_recommendations:
                    collection_totals[callnumber] = c_total
                    gg_recommendations[callnumber] = gg_withdrawl
                else:
                    collection_totals[callnumber] += c_total
                    gg_recommendations[callnumber] += gg_withdrawl

    with open("stacked_data.csv", "w", newline="") as csvfile:
        fieldnames = [
            "Callnumber",
            # "Book Total",
            # "GreenGlass Recommendations",
            "Exempt from review after quantitative analysis",
            "Retained based on qualitative analysis",
            "Donated to Better World Books",
            "Retained At Faculty Request",
            "Retained to Personal Collection"
        ]
        writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
        writer.writeheader()
        for key in department_counts:
            writer.writerow({
                fieldnames[0]: key,
                # fieldnames[1]: collection_totals[key],
                fieldnames[1]: max(0, collection_totals[key] - gg_recommendations[key]),
                fieldnames[2]: max(0, gg_recommendations[key] - department_counts[key]["total"]),
                fieldnames[3]: max(0, department_counts[key]["total"] - department_counts[key]["retain"] - department_counts[key]["personal"]),
                fieldnames[4]: department_counts[key]["retain"],
                fieldnames[5]: department_counts[key]["personal"],
            })

    box_folder = "reports/%s/box_charts" % folder
    data_folder = "reports/%s/pies_data" % folder
    full_folder = "reports/%s/pies_full" % folder
    stacked_folder = "reports/%s/pies_stacked" % folder

    if not os.path.exists(box_folder):
        os.mkdir(box_folder)
    if not os.path.exists(data_folder):
        os.mkdir(data_folder)
    if not os.path.exists(full_folder):
        os.mkdir(full_folder)
    if not os.path.exists(stacked_folder):
        os.mkdir(stacked_folder)

    bar = ProgressBar(len(collection_totals.keys()))
    for cn in collection_totals:
        '''
        print ("%s: %s / %s (%s / %s)" % (
            cn.rjust(2),
            str(gg_recommendations[cn]).rjust(4),
            str(collection_totals[cn]).ljust(6),
            str(department_counts[cn]["retain"] + department_counts[cn]["personal"]).rjust(4),
            str(department_counts[cn]["total"]).ljust(4),
        ))
        '''
        if collection_totals[cn] > 0:
            exempt = max(0, collection_totals[cn] - gg_recommendations[cn])
            retain_qual = max(0, gg_recommendations[cn] - department_counts[cn]["total"])
            donated = max(0, department_counts[cn]["total"] - department_counts[cn]["retain"] - department_counts[cn]["personal"])

            with open(data_folder + "/%s.csv" % cn, "w") as csvfile:
                csvfile.write("%s,%%,#\n" % cn)
                csvfile.write("Total books,1,%d\n" % collection_totals[cn])
                csvfile.write("Exempt from review after quantitative analysis,%f,%d\n" % (exempt / collection_totals[cn], exempt))
                csvfile.write("Retained based on qualitative analysis,%f,%d\n" % (retain_qual / collection_totals[cn], retain_qual))
                csvfile.write("Retained based on faculty feedback,%f,%d\n" % (department_counts[cn]["retain"] / collection_totals[cn], department_counts[cn]["retain"]))
                csvfile.write("Donated to faculty on request,%f,%d\n" % (department_counts[cn]["personal"] / collection_totals[cn], department_counts[cn]["personal"]))
                csvfile.write("Donated to Better World Books,%f,%d\n" % (donated / collection_totals[cn], donated))

            pie_chart(stacked_folder + "/%s_stacked.png" % cn, {
                "total": collection_totals[cn],
                "title": cn,
                "arcs": [
                    {
                        "level": 0,
                        "value": collection_totals[cn],
                        "color": (148, 156, 166), # grey
                        "label": "Total Books\n%s" % comma(collection_totals[cn]),
                    },
                    {
                        "level": 0,
                        "value": gg_recommendations[cn],
                        "color": (193, 205,  35), # green
                        "label": "Qualitative Analysis\n%s - %.2f%%" % (
                            comma(gg_recommendations[cn]),
                            100 * gg_recommendations[cn] / collection_totals[cn]
                        ),
                    },
                    {
                        "level": 1,
                        "value": department_counts[cn]["retain"],
                        "color": (248, 151,  40), # orange
                        "label": "Retained By Request\n%s - %.2f%%" % (
                            comma(department_counts[cn]["retain"]),
                            100 * department_counts[cn]["retain"] / collection_totals[cn]
                        ),
                    },
                    {
                        "level": 1,
                        "value": department_counts[cn]["personal"],
                        "color": (255, 220,  79), # yellow
                        "label": "Donated to Faculty\n%s - %.2f%%" % (
                            comma(department_counts[cn]["personal"]),
                            100 * department_counts[cn]["personal"] / collection_totals[cn]
                        ),
                    },
                    {
                        "level": 1,
                        "value": donated,
                        "color": ( 80, 145, 205), # blue
                        "label": "Donated to Better World\n%s - %.2f%%" % (
                            comma(donated),
                            100 * donated / collection_totals[cn]
                        ),
                    },
                ],
            })

            pie_chart(full_folder + "/%s_full.png" % cn, {
                "total": collection_totals[cn],
                "title": cn,
                "arcs": [
                    {
                        "level": 0,
                        "value": exempt,
                        "color": (  0, 112, 192), # blue
                        "label": "Exempt via\nquantitative analysis\n%s - %.2f%%" % (
                            comma(exempt),
                            100 * exempt / collection_totals[cn]
                        ),
                    },
                    {
                        "level": 0,
                        "value": retain_qual,
                        "color": (255, 255,   0), # yellow
                        "label": "Retained via\nqualitative analysis\n%s - %.2f%%" % (
                            comma(retain_qual),
                            100 * retain_qual / collection_totals[cn]
                        ),
                    },
                    {
                        "level": 0,
                        "value": department_counts[cn]["retain"],
                        "color": (255,   0,   0), # red
                        "label": "Retained based\non Feedback\n%s - %.2f%%" % (
                            comma(department_counts[cn]["retain"]),
                            100 * department_counts[cn]["retain"] / collection_totals[cn]
                        ),
                    },
                    {
                        "level": 0,
                        "value": department_counts[cn]["personal"],
                        "color": ( 84, 130,  53), # dark green
                        "label": "Donated to Faculty\n%s - %.2f%%" % (
                            comma(department_counts[cn]["personal"]),
                            100 * department_counts[cn]["personal"] / collection_totals[cn]
                        ),
                    },
                    {
                        "level": 0,
                        "value": donated,
                        "color": (146, 208,  80), # green
                        "label": "Donated to Better World\n%s - %.2f%%" % (
                            comma(donated),
                            100 * donated / collection_totals[cn]
                        ),
                    },
                ],
            })

            retain_label  = "Retained based on feedback\n(%s - %.2f%%)" % (
                                comma(department_counts[cn]["retain"]),
                                100 * department_counts[cn]["retain"] / collection_totals[cn]
                            )
            to_faculty_label  = "Donated to Faculty\n(%s - %.2f%%)" % (
                                    comma(department_counts[cn]["personal"]),
                                    100 * department_counts[cn]["personal"] / collection_totals[cn]
                                )
            donated_label = "Donated to Better World\n(%s - %.2f%%)" % (
                                comma(donated),
                                100 * donated / collection_totals[cn]
                            )
            box_chart(box_folder + "/%s_box.png" % cn, {
                "total": collection_totals[cn],
                "key": [
                        { "color": (248, 151,  40), "label": retain_label },
                        { "color": (  0, 146, 143), "label": to_faculty_label },
                        { "color": (193, 205,  35), "label": donated_label },
                ],
                "values": [
                    [
                        { "value": department_counts[cn]["retain"], "color": (248, 151,  40), "label": retain_label.replace("\n", " ") },
                        { "value": department_counts[cn]["personal"], "color": (  0, 146, 143), "label": to_faculty_label.replace("\n", " ") },
                        { "value": donated, "color": (193, 205,  35), "label": donated_label.replace("\n", " ") },
                    ],
                    [
                        { "value": retain_qual, "color": ( 80, 145, 205), "label": "Retained via qualitative analysis (%s - %.2f%%)" % (
                            comma(retain_qual),
                            100 * retain_qual / collection_totals[cn]
                        )}
                    ],
                    [
                        { "value": exempt, "color": (255, 210,  79), "label": "Exempt from review after quantitative analysis (%s - %.2f%%)" % (
                            comma(exempt),
                            100 * exempt / collection_totals[cn]
                        )}
                    ],
                ]
            })
        bar.progress()
    bar.finish()
    return {
        "greenglass": gg_recommendations,
        "book_totals": collection_totals,
    }

# Compile all resources into weeding_master
weeding_data_books = {}
weeding_data_by_month = {}
weeding_dirs = [dir.path for dir in os.scandir("sources/") if dir.is_dir()]
print ("Gathering All Weeding Data...")
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
'''
print ("\nGenerating callnumber breakdowns...")
totals = callnumber_breakdowns(cumulative_folder)
'''
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
totals.update({ "retention": all_book_requests })
json.dump(totals, open("retention_data.json", "w"), indent=4, sort_keys=True)
