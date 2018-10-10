import sqlite3
from xlrd import open_workbook  # Excel files
from typing import Dict, Optional

from .utils import normalize_callnumber

SECTIONS = []


def get_callnumber_section(callnumber: str, conn = None) -> Optional[str]:
    global SECTIONS
    if not SECTIONS:
        if not conn:
            conn = sqlite3.connect("database.sqlite")
        conn.row_factory = lambda cursor, row: row[0]
        cursor = conn.cursor()
        cursor.execute("SELECT cn_section FROM librarian_assignments ORDER BY LENGTH(cn_section) DESC")
        SECTIONS = cursor.fetchall()
    if not callnumber:
        raise ValueError("empty callnumber")
    for sec in SECTIONS:
        if callnumber.startswith(sec):
            return sec
    raise ValueError("invalid callnumber: %s" % callnumber)


def parse_source_file(filepath, conn = None) -> Optional[Dict]:
    global SECTIONS

    # Get callnumber section
    path = filepath.split("\\")
    filename = path[len(path) - 1]
    if filename[0] == "~":
        print("Make sure %s isn't open in Excel (Skipping)" % path[len(path) - 1])
        return None

    posted_file = {"name": path[len(path) - 1]}
    with open_workbook(filepath) as excel_book:
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
                    print("x\t%s" % filename)
                    print("x\t%s" % rvalues[i])
                    raise ValueError("Invalid columns")
        books = []
        for row in range(1, sheet.nrows):
            rvalues = sheet.row_values(row)
            # No barcode == microfilm
            if not rvalues[books_columns["barcode"]]:
                # print (rvalues[books_columns["callnumber"]], rvalues[books_columns["title"]])
                continue
            # if not rvalues[books_columns["callnumber"]].startswith(filename[0]):
            #     continue
            book = {}
            for key in books_columns:
                book[key] = rvalues[books_columns[key]]
            # Special treatment (integers and sorting)
            book["barcode"] = str(book["barcode"]).split(".")[0]
            book["callnumber_sort"] = normalize_callnumber(book["callnumber"])
            book["year"] = str(book["year"]).split(".")[0]
            try:
                book["cn_section"] = get_callnumber_section(book["callnumber_sort"], conn if conn else None)
            except ValueError as e:
                print(book)
            books.append(book)
        posted_file["books"] = books
    return posted_file
