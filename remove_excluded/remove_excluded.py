import os
import sqlite3
import time
import win32com.client as win32

from shutil import copy
from xlrd import open_workbook  # Excel files

import sys
sys.path.append("..")
from src.posted_files import parse_source_file

if not os.path.exists("../database.sqlite"):
    print("WTF")
    exit(0)

conn = sqlite3.connect("../database.sqlite")
cursor = conn.cursor()

log_text = ""
def log(msg):
    global log_text
    log_text += msg + "\n"
    print (msg)

# Fire up Excel
excel = win32.gencache.EnsureDispatch("Excel.Application")


def filter_folder(in_dir, out_dir):
    if not os.path.exists(out_dir):
        os.mkdir(out_dir)

    try:
        excel_files = [file for file in os.scandir(in_dir) if file.is_file() and file.name[-4:] == "xlsx"]
        for stat in excel_files:
            source_name = stat.name
            parts = source_name[0:-5].split("_")
            count = int(parts.pop())
            name = "_".join(parts)

            log ("---")
            log (source_name)
            log ("%s\t%s" % (name, count))

            wb = excel.Workbooks.Open(os.path.abspath(stat.path))
            ws = wb.Sheets(1)
            # ws.Name = ("%s_updated" % ws.Name)[0:32] # limit length

            parsed_file = None
            parsed_file = parse_source_file(os.path.abspath(stat.path), conn)
            '''
            try:
                parsed_file = parse_source_file(os.path.abspath(stat.path), conn)
            except ValueError as e:
                print(e)
                continue
            '''
            if parsed_file is None:
                continue
            remove = []
            index = 2
            for book in parsed_file["books"]:
                # Skip if excluded
                cursor.execute("""
                    SELECT excluded_sets.reason FROM excluded_sets
                        INNER JOIN excluded_barcodes on excluded_sets.set_id = excluded_barcodes.set_id
                        WHERE excluded_barcodes.barcode=?""", (book["barcode"],))
                reason = cursor.fetchone()
                if reason is not None:
                    remove.append(index)
                    log ("\t%s: %s" % (book["barcode"], reason[0]))
                index += 1
            # Remove rows from Excel file
            for i in range(len(remove) - 1, -1, -1):
                row = remove[i]
                # log (i, row)
                ws.Rows("%d:%d" % (row, row)).Select()
                excel.Selection.Delete(Shift=win32.constants.xlUp)

            if len(remove) == 0:
                log ("no changes")
                log ("\tFor prompt: (Don't Save)")
                copy(stat.path, "%s/%s" % (out_dir, source_name))
            else:
                log ("%d changes" % len(remove))
                log ("\tFor prompt: (Overwrite / Save)")
                wb.SaveAs(os.path.abspath("%s/%s_%d" % (out_dir, name, count - len(remove))))
            wb.Close()
            log ("%s/%s_%d.xlsx" % (out_dir, name, count - len(remove)))
    finally:
        print (" - closing Excel")
        excel.Application.Quit()
        print (" - closed")
        log_file = open("./remove_checkedout.log", "a")
        log_file.write("\n\n--------------\n%s\n" % time.asctime(time.localtime(time.time())))
        log_file.write(log_text)


filter_folder("src", "./out")
'''
filter_folder("../../../../Dropbox (Villanova)/Collection Review Task Force - Public/Archived/2018 February/Including checked out items/", "./out/2018 February")
filter_folder("../../../../Dropbox (Villanova)/Collection Review Task Force - Public/Archived/2018 March/Including checked out items/", "./out/2018 March")
filter_folder("../../../../Dropbox (Villanova)/Collection Review Task Force - Public/Archived/2018 April/Including checked out items/", "./out/2018 April")
filter_folder("../../../../Dropbox (Villanova)/Collection Review Task Force - Public/Archived/2018 May/Including checked out items/", "./out/2018 May")
filter_folder("../../../../Dropbox (Villanova)/Collection Review Task Force - Public/Archived/2018 September/Including checked out items/", "./out/2018 September")
filter_folder("../../../../Dropbox (Villanova)/Collection Review Task Force - Public/Archived/2018 October/Including checked out items/", "./out/2018 October")
filter_folder("../../../../Dropbox (Villanova)/Collection Review Task Force - Public/Archived/2018 November/Including checked out items/", "./out/2018 November")
filter_folder("../../../../Dropbox (Villanova)/Collection Review Task Force - Public/Archived/2018 December/Including checked out items/", "./out/2018 December")
filter_folder("../../../../Dropbox (Villanova)/Collection Review Task Force - Public/Archived/2019 January/Including checked out items/", "./out/2019 January")
filter_folder("../../../../Dropbox (Villanova)/Collection Review Task Force - Public/Archived/2019 February/Including checked out items/", "./out/2019 February")
filter_folder("../../../../Dropbox (Villanova)/Collection Review Task Force - Public/Archived/2019 March/Including checked out items/", "./out/2019 March")
'''
'''
filter_folder("../sources/2018 February", "./out/2018 February")
filter_folder("../sources/2018 March", "./out/2018 March")
filter_folder("../sources/2018 April", "./out/2018 April")
filter_folder("../sources/2018 May", "./out/2018 May")
filter_folder("../sources/2018 September", "./out/2018 September")
filter_folder("../sources/2018 October", "./out/2018 October")
filter_folder("../sources/2018 November", "./out/2018 November")
filter_folder("../sources/2018 December", "./out/2018 December")
filter_folder("../sources/2019 January", "./out/2019 January")
filter_folder("../sources/2019 February", "./out/2019 February")
filter_folder("../sources/2019 March", "./out/2019 March")
'''

conn.close()
