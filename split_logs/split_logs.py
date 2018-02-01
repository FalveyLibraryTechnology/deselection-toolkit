import csv
import datetime
import json
import os
import sys

from checksumdir import dirhash # folder md5
from xlrd import open_workbook  # Excel files

csv.field_size_limit(sys.maxsize)

# Barcodes removed for being checked out
CHECKED_OUT_BARCODES = [str(int(x.strip())) for x in open("../checked_out/checkedout_since_greenglass.txt").read().split("\n")]

def make_unique(arr):
    return list(set(filter(None, arr)))

def parse_crtf_dir(reports_dir):
    barcodes = []
    for dirpath, dirnames, filenames in os.walk(reports_dir):
        for filename in filenames:
            with open_workbook(os.path.join(dirpath, filename)) as book:
                sheet = book.sheet_by_index(0)
                rvalues = sheet.row_values(0)
                column_names = ["Barcode"]
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

                for row in range(1, sheet.nrows):
                    rvalues = sheet.row_values(row)
                    barcode = str(rvalues[columns[0]]).split(".")[0] # Remove decimaled barcodes
                    barcodes.append(barcode)
    return make_unique(barcodes)

def parse_form(row):
    global all_barcodes, month_by_index

    by_month = {}
    parts = row[4].split("Barcode:\n")
    headers = parts[0]
    book_submissions = parts[1:]
    for bt in book_submissions:
        bc = 0
        blines = bt.split('\n')
        barcode = blines[0].strip()
        try:
            index = all_barcodes.index(barcode)
            for limit in month_by_index:
                if index < limit:
                    month = month_by_index[limit]
                    if not month in by_month:
                        by_month[month] = [headers]
                    by_month[month].append(bt)
                    break
        except Exception as e:
            if not barcode in CHECKED_OUT_BARCODES:
                print ("\tmissing barcode: %s (%s)" % (barcode, row[0]))
    for month in by_month:
        by_month[month] = [row[0], row[1], row[2], row[3], "Barcode:\n".join(by_month[month]).strip()]
    return by_month

all_barcodes = []
month_by_index = {}
weeding_dirs = [dir.path for dir in os.scandir("../sources/") if dir.is_dir()]
print ("Gathering All Weeding Data...")
for dir in weeding_dirs:
    print (dir)
    month = dir.split("/")[2]
    print ("\t%s" % month)
    month_barcodes = parse_crtf_dir(dir)
    month_by_index[len(all_barcodes) + len(month_barcodes)] = month
    all_barcodes.extend(month_barcodes)

open("debug-all_barcodes.txt", "w").write("\n".join(all_barcodes));
print (month_by_index)

print ("\nAnalyzing Consolidated Log File...")
file = csv.reader(open("input.csv", encoding="utf-8"))
form_rows = []
header = True
for row in file:
    if header:
        header = False
        continue
    form_rows.append(row)
form_rows.sort(key=lambda r: datetime.datetime.strptime(r[0], "%b %d, %Y, %I:%M:%S %p"))
forms_by_month = {}
for row in form_rows:
    split_form = parse_form(row)
    for month in split_form:
        if not month in forms_by_month:
            forms_by_month[month] = []
        forms_by_month[month].append(split_form[month])

if not os.path.exists('out/'):
    os.mkdir('out/')
for month in forms_by_month:
    print ("\t%s: %d" % (month, len(forms_by_month[month])))
    with open("out/%s-log.csv" % month, "w", encoding="utf-8", newline="") as outfile:
        outfile.write("Date,Level,Channel,User,Message\n")
        writer = csv.writer(outfile)
        writer.writerows(forms_by_month[month])
