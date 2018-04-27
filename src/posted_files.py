import os
import re

from xlrd import open_workbook  # Excel files

from .utils import normalize_callnumber

def parse_source_dir(month_dir):
    posted_files = []

    for dirpath, dirnames, filenames in os.walk(month_dir):
        for filename in filenames:
            posted_file = {
                "name": filename,
                "month": month_dir
            }
            with open_workbook(os.path.join(dirpath, filename)) as excel_book:
                sheet = excel_book.sheet_by_index(0)
                rvalues = sheet.row_values(0)
                column_names = {
                    "Display Call Number": "callnumber",
                    "Barcode": "barcode",
                    "Title": "title",
                    "Author": "author",
                    "Publication Year": "year",
                }
                books_columns = {}
                for name in column_names:
                    if name in rvalues:
                        books_columns[column_names[name]] = rvalues.index(name)
                    else:
                        for i in range(len(rvalues)):
                            print ("x\t%s:" % filename)
                            print ("x\t%s" % (i, rvalues[i]))
                            raise Error("Invalid columns")

                check_letter = re.search("^([A-Z]+)", filename[0]).group(1)
                books = []
                for row in range(1, sheet.nrows):
                    rvalues = sheet.row_values(row)
                    if not rvalues[books_columns["callnumber"]].startswith(check_letter):
                        continue
                    book = {}
                    for key in books_columns:
                        book[key] = str(rvalues[books_columns[key]]).split(".")[0]
                    # Special treatment
                    book["year"] = str(rvalues[books_columns["year"]]).split(".")[0]
                    book["callnumber"] = str(rvalues[books_columns["callnumber"]]).split(".")[0]
                    book["callnumber_sort"] = normalize_callnumber(book["callnumber"])
                    books.append(book)
            posted_file["books"] = books
            posted_files.append(posted_file)
    return posted_files
