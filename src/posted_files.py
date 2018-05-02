import os
import re

from xlrd import open_workbook  # Excel files

from .utils import make_unique, normalize_callnumber

SECTIONS = ["DAW", "DJK", "QA", "QB", "QC", "QD", "QE", "SB", "SD", "SF", "SH", "SK", "TA", "TC", "TD", "TE", "TF", "TG", "TH", "TJ", "TK", "TL", "TN", "TP", "TS", "TT", "TX", "BL", "BM", "BP", "BQ", "BR", "BS", "BT", "BV", "BX", "PA", "ZA", "JA", "JC", "JF", "JJ", "JK", "JL", "JN", "JQ", "JS", "JV", "JX", "JZ", "CB", "CC", "CD", "CE", "CJ", "CN", "CR", "CS", "CT", "DA", "DB", "DC", "DD", "DE", "DF", "DG", "DH", "DJ", "DK", "DP", "DQ", "DR", "DS", "DT", "DU", "DX", "GN", "GR", "GT", "GV", "HM", "HN", "HQ", "HS", "HT", "HV", "HX", "NA", "NB", "NC", "ND", "NE", "NK", "NX", "TR", "HA", "HB", "HC", "HD", "HE", "HF", "HG", "BF", "GA", "GB", "GC", "GE", "GF", "LA", "LB", "LC", "LD", "LE", "LF", "LG", "LH", "LJ", "LT", "UA", "UB", "UC", "UD", "UE", "UF", "UG", "UH", "VA", "VB", "VC", "VD", "VE", "VF", "VG", "VK", "VM", "BC", "BD", "BH", "QH", "QK", "QL", "QM", "QP", "QR", "RA", "RB", "RC", "RD", "RE", "RF", "RG", "RJ", "RK", "RL", "RM", "RS", "RT", "RV", "RX", "RZ", "BJ", "PE", "PB", "PC", "PD", "PF", "PG", "PH", "PJ", "PK", "PL", "PM", "PQ", "PN", "PR", "PS", "PT", "A", "Q", "S", "T", "J", "C", "D", "E", "F", "N", "Z", "H", "K", "G", "L", "U", "V", "B", "R", "M", "P"]

# TODO: Reviewed count
def parse_source_file(filename):
    global SECTIONS

    # Get callnumber section
    path = filename.split("\\")
    try:
        cn_section = re.search("^([A-Z]+)", path[len(path) - 1]).group(1)
    except AttributeError as e:
        print ("Make sure %s isn't open in Excel (Skipping)" % path[len(path) - 1])
        return None
    for sec in SECTIONS:
        if cn_section.startswith(sec):
            cn_section = sec

    posted_file = {
        "name": path[len(path) - 1],
        "cn_section": cn_section
    }
    with open_workbook(filename) as excel_book:
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
        books = []
        for row in range(1, sheet.nrows):
            rvalues = sheet.row_values(row)
            if rvalues[books_columns["barcode"]] == "":
                continue
            if not rvalues[books_columns["callnumber"]].startswith(cn_section):
                continue
            book = {}
            for key in books_columns:
                book[key] = rvalues[books_columns[key]]
            # Special treatment (integers and sorting)
            book["barcode"] = str(book["barcode"]).split(".")[0]
            book["callnumber_sort"] = normalize_callnumber(book["callnumber"])
            book["year"] = str(book["year"]).split(".")[0]
            books.append(book)
    posted_file["books"] = books
    return posted_file

def parse_source_dir(month_dir):
    posted_files = []

    for dirpath, dirnames, filenames in os.walk(month_dir):
        for filename in filenames:
            parsed_file = parse_source_file(os.path.join(dirpath, filename))
            if parsed_file is None:
                continue
            parsed_file["month"] = month_dir
            posted_files.append(parsed_file)
    return posted_files
