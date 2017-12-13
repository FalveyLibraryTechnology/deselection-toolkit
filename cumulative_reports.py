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
                        print ("\t\t\tAuto-detected columns: %s" % ", ".join([rvalues[x] for x in columns]))

                    for row in range(1, sheet.nrows):
                        rvalues = sheet.row_values(row)
                        barcode = str(rvalues[columns[1]]).split(".")[0] # Remove decimaled barcodes
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

retained_with_duplicates = []
def parseForm(row, month):
    global all_retained_books, all_faculty

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

    book_submissions = form.split('Barcode:\n')[1:]
    books = {}
    faculty_list = []
    personal_list = []
    overridden = []
    for bt in book_submissions:
        bc = 0
        blines = bt.split('\n')
        barcode = blines[0].strip()
        b = {
            "date": date,
            "faculty": faculty["name"],
            "month": month,
        }

        # Get title from master list
        # while blines[bc] != 'Title:':
        #     bc += 1
        # b['title'] = blines[bc + 1].strip()

        while blines[bc] != 'Destination:':
            # print (bc, len(blines), blines[bc])
            bc += 1
        b["for_personal"] = blines[bc + 1].strip() == 'Patron'
        # Check if book already retained for collection
        if barcode in all_retained_books and not all_retained_books[barcode]["for_personal"]:
            # print ("Overridden by Collection: %s" % barcode)
            if not barcode in overridden:
                overridden.append(barcode)
        elif b["for_personal"]:
            personal_list.append(barcode)

        while blines[bc] != 'Comment:':
            bc += 1
        b['comment'] = '\n'.join(blines[bc + 1:]).strip()

        # Personal collection overridden
        faculty_list.append(barcode)
        for name in all_faculty:
            if barcode in all_faculty[name]["personal"]:
                all_faculty[name]["personal"].remove(barcode)
                if not barcode in overridden:
                    overridden.append(barcode)
                # print ("Overridden by Earlier Claim: %s" % barcode)
        books[barcode] = b
        b["barcode"] = barcode
        retained_with_duplicates.append(b)

    faculty["books"] = faculty_list
    faculty["personal"] = personal_list

    return books, faculty, overridden

def book_to_row_headers():
    return '"Callnumber","Barcode","Publication Year","Title","Author"'
def book_to_row(book):
    return '"%s",%s,%s,"%s","%s"' % (
        book["callnumber"],
        book["barcode"],
        book["year"],
        book["title"],
        book["author"],
    )

def create_retention_by_callnumber(retain_barcodes, month):
    global all_faculty, all_retained_books, weeding_data_books
    books = []
    for barcode in retain_barcodes:
        if barcode in weeding_data_books:
            for name in all_faculty:
                if barcode in all_faculty[name]["books"]:
                    books.append(weeding_data_books[barcode])
                    break
    books.sort(key=lambda b: b["callnumber_sort"])
    with open('reports/%s/all-retention-by-callnumber.csv' % month, 'w', encoding="utf8") as outfile:
        outfile.write('%s,"%s","%s"\n' % (book_to_row_headers(),"Requesting Faculty","Destination"))
        for b in books:
            record = all_retained_books[b["barcode"]]
            outfile.write('%s,"%s","%s"\n' % (book_to_row(b), record["faculty"], "Personal" if record["for_personal"] else "Retain"))

def create_retention_by_faculty(retain_barcodes, month):
    global all_faculty, weeding_data_books
    with open('reports/%s/all-retention-by-faculty.csv' % month, 'w', encoding="utf8") as outfile:
        for name in all_faculty:
            faculty = all_faculty[name]
            books = []
            for barcode in faculty["books"]:
                personal = barcode in faculty["personal"]
                if barcode in retain_barcodes and barcode in weeding_data_books:
                    books.append((weeding_data_books[barcode]["callnumber_sort"], (barcode, personal)))
            books.sort(key=lambda b: b[0])
            if len(books) > 0:
                outfile.write('"%s","%s","%s"\n' % (faculty["name"], faculty["department"], faculty["address"]))
                for book in books:
                    barcode, personal = book[1]
                    outfile.write(',"%s",%s\n' % ("Personal" if personal else "Retain", book_to_row(weeding_data_books[barcode])))

def create_personal_by_callnumber(retain_barcodes, month):
    global all_faculty, all_retained_books, weeding_data_books

    books = []
    for barcode in retain_barcodes:
        for name in all_faculty:
            if barcode in all_faculty[name]["personal"]:
                books.append(weeding_data_books[barcode])
    books.sort(key=lambda b: b["callnumber_sort"])
    with open('reports/%s/for-personal-collections-by-callnumber.csv' % month, 'w', encoding="utf8") as outfile:
        outfile.write('%s,"Requesting Faculty","Campus Address"\n' % book_to_row_headers())
        for b in books:
            record = all_retained_books[b["barcode"]]
            outfile.write('%s,"%s","%s"\n' % (book_to_row(b), record["faculty"], all_faculty[record["faculty"]]["address"]))

def create_personal_by_faculty(retain_barcodes, month):
    global all_faculty, all_retained_books, weeding_data_books
    with open('reports/%s/for-personal-collections-by-faculty.csv' % month, 'w', encoding="utf8") as outfile:
        for name in all_faculty:
            faculty = all_faculty[name]
            books = []
            for barcode in faculty["personal"]:
                if barcode in retain_barcodes and barcode in weeding_data_books:
                    books.append(weeding_data_books[barcode])
            books.sort(key=lambda b: b["callnumber_sort"])
            if len(books) > 0:
                outfile.write('"%s","%s","%s"\n' % (faculty["name"], faculty["department"], faculty["address"]))
                for b in books:
                    record = all_retained_books[b["barcode"]]
                    outfile.write(',%s\n' % (book_to_row(b)))

def create_emails(retain_barcodes, month):
    global all_faculty, all_retained_books, weeding_data_books

    faculty_emails = {}
    for barcode in retain_barcodes:
        if barcode in all_retained_books:
            book = all_retained_books[barcode]
            if len(all_faculty[book["faculty"]]["personal"]) > 0:
                if not book["faculty"] in faculty_emails:
                    faculty_emails[book["faculty"]] = {
                        "theirs": [],
                        "in_library": [],
                        "too_late": [],
                    }
                if barcode in all_faculty[book["faculty"]]["personal"]:
                    faculty_emails[book["faculty"]]["theirs"].append(weeding_data_books[barcode]["title"])
                elif book["for_personal"]:
                    faculty_emails[book["faculty"]]["too_late"].append(weeding_data_books[barcode]["title"])
                else:
                    faculty_emails[book["faculty"]]["in_library"].append(weeding_data_books[barcode]["title"])
    with open('reports/%s/personal-retention-emails.csv' % month, 'w', encoding="utf8") as outfile:
        writer = csv.writer(outfile)
        writer.writerow(["Faculty", "Department", "Email"])
        for name in faculty_emails:
            faculty = faculty_emails[name]
            receiving = ""
            if len(faculty["theirs"]) > 0:
                receiving = "\n\nYou will be receiving the following books:\n\n - %s" % "\n - ".join(make_unique(faculty["theirs"]))
            staying = ""
            if len(faculty["in_library"]) > 0:
                staying = "\n\nThe following books you requested will be kept in the collection:\n\n - %s" % "\n - ".join(make_unique(faculty["in_library"]))
            other = ""
            if len(faculty["too_late"]) > 0:
                if len(faculty["theirs"]) > 0 or len(faculty["in_library"]) > 0:
                    if len(faculty["too_late"]) == 1:
                        other = "\n\nThe final book you requested was requested by another faculty member before you, so you will not be receiving this item."
                    else:
                        other = "\n\nThe remaining %d books you requested were requested by another faculty member before you requested them, so you will not be receiving those items."
                else:
                    if len(faculty["too_late"]) == 1:
                        other = "\n\nUnfortunately, the book you requested was requested by another faculty member before you, so we're sorry to say that you will not be receiving your requested item."
                    else:
                        other = "\n\nUnfortunately, all the books you requested were requested by another faculty member before you requested them, so we're sorry to say that you will not be receiving your requested items."
            writer.writerow([name, all_faculty[name]["department"],
"""Dear %s,

[These are the rules]%s%s%s

Stay sexy, don't get murdered,
""" % (name, receiving, staying, other)])

def create_master_list(month_barcodes, retain_barcodes, month):
    global weeding_data_books

    # Filter for unique
    month_barcodes = make_unique(month_barcodes)
    retain_barcodes = make_unique(retain_barcodes)

    master_list = []
    for barcode in month_barcodes:
        if not barcode in retain_barcodes:
            master_list.append(weeding_data_books[barcode])
    master_list.sort(key=lambda b: b["callnumber_sort"])
    print ("%s master list: %d - %d = %d === %d" % (
        month,
        len(month_barcodes),
        len(retain_barcodes),
        len(month_barcodes) - len(retain_barcodes),
        len(master_list),
    ))

    # Check logs for barcodes
    log_file = "sources/%s-log.csv" % month
    log_file_text = ""
    if os.path.exists(log_file):
        print ("\tChecking against %s..." % log_file)
        log_file_text = open(log_file).read()
    else:
        print ("\tChecking against all logs...")
        log_files = [file.name for file in os.scandir("sources/") if file.is_file()]
        for log in log_files:
            log_file_text += open("sources/%s" % log).read()
    if len(log_file_text) > 0:
        for book in master_list:
            if book["barcode"] in log_file_text:
                print("\t\tERROR: %s" % book["barcode"])

    with open('reports/%s/master-pull-list.csv' % month, 'w', encoding="utf8") as outfile:
        outfile.write('%s,"Action Taken"\n' % book_to_row_headers())
        for b in master_list:
            outfile.write('%s,\n' % book_to_row(b))

def create_department_graph(month_barcodes, retain_barcodes, month):
    global all_faculty, all_retained_books, department_counts, weeding_data_books

    department_counts = {}
    for barcode in month_barcodes:
        dept_match = re.search('^([A-Z]+)', weeding_data_books[barcode]["callnumber"])
        department = dept_match.group(1)
        if not department in department_counts:
            department_counts[department] = {
                "name": department,
                "total": 1,
                "retain": 0,
                "personal": 0,
            }
        else:
            department_counts[department]["total"] += 1

    for barcode in retain_barcodes:
        if not barcode in weeding_data_books or not barcode in all_retained_books:
            continue
        dept_match = re.search('^([A-Z]+)', weeding_data_books[barcode]["callnumber"])
        department = dept_match.group(1)
        for name in all_faculty:
            if barcode in all_faculty[name]["books"]:
                department_counts[department]["retain"] += 1
            if barcode in all_faculty[name]["personal"]:
                department_counts[department]["retain"] += 1
                department_counts[department]["personal"] += 1

    department_bars = []
    for department in department_counts:
        department_bars.append([
            department_counts[department]["total"],
            department_counts[department]["retain"],
            department_counts[department]["personal"],
            department_counts[department]["name"],
        ])
    department_bars.sort(key=lambda x: x[0], reverse=True)
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
        "reports/%s/callnumber_areas_sorted.png" % month,
        [bar[:3] for bar in department_bars],
        key=["Total Marked", "Total Retained", "Retained for Personal"],
        labels=department_labels,
        title=month
    )

    department_bars.sort(key=lambda x: x[3], reverse=False)
    department_labels = []
    for bar in department_bars:
        name = bar.pop()
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
        "reports/%s/callnumber_areas.png" % month, department_bars,
        key=["Total Marked", "Total Retained", "Retained for Personal"],
        labels=department_labels,
        title=month
    )

def create_faculty_graph(retain_barcodes, month):
    global all_faculty, all_retained_books

    added_names = []
    for barcode in retain_barcodes:
        if not barcode in all_retained_books:
            continue
        name = all_retained_books[barcode]["faculty"]
        if not name in added_names:
            added_names.append(name)
    sorted_faculty = []
    for name in added_names:
        sorted_faculty.append({
            "name": all_faculty[name]["name"],
            "department": all_faculty[name]["department"],
            "books": len(all_faculty[name]["books"]),
            "personal": len(list(filter(lambda b: b in all_faculty[name]["personal"], all_faculty[name]["books"]))),
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
        key=["Total Requested", "Requested for Personal"],
        labels=faculty_labels,
        title=month
    )

def callnumber_breakdowns(month_barcodes, retain_barcodes, folder):
    global all_retained_books, department_counts, weeding_data_books

    department_counts = {}
    for barcode in month_barcodes:
        dept_match = re.search('^([A-Z]+)', weeding_data_books[barcode]["callnumber"])
        department = dept_match.group(1)
        if not department in department_counts:
            department_counts[department] = {
                "name": department,
                "total": 1,
                "retain": 0,
                "personal": 0,
            }
        else:
            department_counts[department]["total"] += 1

    for barcode in retain_barcodes:
        if not barcode in weeding_data_books or not barcode in all_retained_books:
            continue
        dept_match = re.search('^([A-Z]+)', weeding_data_books[barcode]["callnumber"])
        department = dept_match.group(1)
        if all_retained_books[barcode]["for_personal"]:
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
        ];
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
print ("Weeding Files")
for dir in weeding_dirs:
    month = dir.split("/")[1]
    print ("\t%s" % month)
    month_data = parse_crtf_dir(dir)
    weeding_data_books.update(month_data)
    weeding_data_by_month[month] = make_unique(month_data.copy().keys())

all_faculty = {}
all_retained_books = {}
retention_by_month = {}
print ("Log Files")
log_files = [file.name for file in os.scandir("sources/") if file.is_file()]
for log in log_files:
    month = log.split("-")[0]
    retention_by_month[month] = []
    print ("\t%s" % month)

    header = True
    file = csv.reader(open("sources/%s" % log))
    month_overridden = 0
    for row in file:
        if header:
            header = False
            continue
        # date = datetime.datetime.strptime(row[0], '%b %d, %Y, %I:%M:%S %p')
        books, faculty, overridden = parseForm(row, month)
        month_overridden += len(overridden)
        for barcode in books:
            if barcode in weeding_data_books:
                all_retained_books[barcode] = books[barcode]
            else:
                print ("missing barcode: %s (%s, %s)" % (barcode, faculty["name"], faculty["department"]))
        retention_by_month[month].extend(books.keys())
        if faculty["name"] in all_faculty:
            # Update address
            if len(faculty["address"]) > len(all_faculty[faculty["name"]]["address"]):
                all_faculty[faculty["name"]]["address"] = faculty["address"]
            # Update department
            if len(faculty["department"]) > len(all_faculty[faculty["name"]]["department"]):
                all_faculty[faculty["name"]]["department"] = faculty["department"]
            all_faculty[faculty["name"]]["books"].extend(faculty["books"])
        else:
            all_faculty[faculty["name"]] = faculty
    retention_by_month[month] = make_unique(retention_by_month[month])
    print ("\t\tOverridden: %d" % month_overridden)

for month in retention_by_month:
    if not os.path.exists('reports/%s' % month):
        os.mkdir('reports/%s' % month)
    create_retention_by_callnumber(retention_by_month[month], month)
    create_retention_by_faculty(retention_by_month[month], month)
    create_personal_by_callnumber(retention_by_month[month], month)
    create_personal_by_faculty(retention_by_month[month], month)
    create_emails(retention_by_month[month], month)
    # Master list
    create_master_list(weeding_data_by_month[month], retention_by_month[month], month)
    # Graphs
    create_department_graph(weeding_data_by_month[month], retention_by_month[month], month)
    create_faculty_graph(retention_by_month[month], month)

# Cumulative Records
cumulative_folder = "Since October 2017"
if not os.path.exists('reports/%s' % cumulative_folder):
    os.mkdir('reports/%s' % cumulative_folder)
all_retained_books_keys = all_retained_books.keys()
create_retention_by_callnumber(all_retained_books_keys, cumulative_folder)
create_retention_by_faculty(all_retained_books_keys, cumulative_folder)
create_personal_by_callnumber(all_retained_books_keys, cumulative_folder)
create_personal_by_faculty(all_retained_books_keys, cumulative_folder)
# Master list
# create_master_list(weeding_data_books.keys(), all_retained_books_keys, cumulative_folder)
# Graphs
create_department_graph(weeding_data_books.keys(), all_retained_books_keys, cumulative_folder)
create_faculty_graph(all_retained_books_keys, cumulative_folder)

print ("\nGenerating callnumber breakdowns...")
totals = callnumber_breakdowns(weeding_data_books.keys(), all_retained_books_keys, cumulative_folder)

print ("\nExport all retention as json...")
owner = {}
retained_with_duplicates.sort(key=lambda x: datetime.datetime.strptime(x["date"], "%b %d, %Y, %I:%M:%S %p"))
for i in range(len(retained_with_duplicates)):
    book = retained_with_duplicates[i]
    if not book["barcode"] in owner:
        owner[book["barcode"]] = i
        continue
    curr = owner[book["barcode"]]
    if not book["for_personal"] and retained_with_duplicates[curr]["for_personal"]:
        owner[book["barcode"]] = i
for i in range(len(retained_with_duplicates)):
    book = retained_with_duplicates[i]
    book["overridden"] = owner[book["barcode"]] != i

retained_with_duplicates.sort(key=lambda x: x["barcode"])
for book in retained_with_duplicates:
    if book["barcode"] in weeding_data_books:
        book.update(weeding_data_books[book["barcode"]])
        book["department"] = all_faculty[book["faculty"]]["department"]
        del book["faculty"]
totals.update({ "retention": retained_with_duplicates })
json.dump(totals, open("retention_data.json", "w"), indent=4, sort_keys=True)
