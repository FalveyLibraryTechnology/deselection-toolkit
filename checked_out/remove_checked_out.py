import csv
import os
import string
import time
import win32com.client as win32
from math import floor
from shutil import copy
from xlrd import open_workbook  # Excel files

log_text = ""
def log(msg):
    global log_text
    log_text += msg + "\n"
    print (msg)

def col_to_letter(col):
    barcode_col = ""
    if col > 26:
        barcode_col = string.ascii_uppercase[floor((col - 1) / 26) - 1]
        col %= 26
    barcode_col += string.ascii_uppercase[col - 1]
    return barcode_col

if not os.path.exists('out/'):
    os.mkdir('out/')

CHECKED_OUT_BARCODES = [int(x) for x in open("checkedout_since_greenglass.txt").read().split("\n")]
print ("Number of items since April 1: %d" % len(CHECKED_OUT_BARCODES))
# print (CHECKED_OUT_BARCODES[0])

excel = win32.gencache.EnsureDispatch('Excel.Application')
excel_files = [file for file in os.scandir(".") if file.is_file() and file.name[-4:] == "xlsx"]
print (excel_files)
for stat in excel_files:
    log ("---")
    source_name = stat.name
    log (source_name)
    log (os.path.abspath(stat.path))
    parts = source_name[0:-5].split("_")
    count = int(parts.pop())
    name = "_".join(parts)
    log ("%s\t%s" % (name, count))

    wb = excel.Workbooks.Open(os.path.abspath(stat.path))
    ws = wb.Sheets(1)
    header_row = 1
    barcode_col = False
    none_count = 0
    while not barcode_col:
        headers = ws.Range("%d:%d" % (header_row, header_row))
        for i in range(1, len(headers)):
            print (header_row, headers[i], i, col_to_letter(i))
            if headers[i].Value == None:
                none_count += 1
                continue
            else:
                none_count = 0
            if none_count > 3:
                header_row += 1
                break
            if headers[i].Value == "Barcode":
                barcode_col = col_to_letter(i)
                log ("%s\t%s" % (headers[i], barcode_col))
                break
    barcodes = ws.Range("%s%d:%s%d" % (barcode_col, header_row + 1, barcode_col, count + 1))
    remove = []
    row = header_row
    for barcode in barcodes:
        row += 1
        # log (row, barcode)
        try:
            barcode = int(barcode)
            if barcode in CHECKED_OUT_BARCODES:
                log ("\t%s\t%d" % (barcode, row))
                remove.append(row)
        except Exception:
            continue
    for i in range(len(remove) - 1, -1, -1):
        row = remove[i]
        # log (i, row)
        ws.Rows("%d:%d" % (row, row)).Select()
        excel.Selection.Delete(Shift=win32.constants.xlUp)

    ws.Name = "%s_updated" % ws.Name

    if len(remove) == 0:
        log ("no changes")
        copy(stat.path, "./out/%s" % source_name)
        log ("\t(Don't Save)")
    else:
        log ("%d changes" % len(remove))
        log ("\t(Save)")
        wb.SaveAs(os.path.abspath("./out/%s_%d" % (name, count - len(remove))))
    wb.Close()
    log ("./out/%s_%d.xlsx" % (name, count - len(remove)))

excel.Application.Quit()
log_file = open("./out/remove_checkedout_report.txt", "w")
log_file.write(time.asctime(time.localtime(time.time())))
log_file.write("\n")
log_file.write(log_text)
