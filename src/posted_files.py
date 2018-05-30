from xlrd import open_workbook  # Excel files
from typing import Dict, Optional

from .utils import normalize_callnumber

SECTIONS = ["DAW", "DJK", "BC", "BD", "BH", "BL", "BF", "BJ", "BM", "BP", "BQ", "BR", "BS", "BT", "BV", "BX",
            "CB", "CC", "CD", "CE", "CJ", "CN", "CR", "CS", "CT",
            "DA", "DB", "DC", "DD", "DE", "DF", "DG", "DH", "DJ", "DK", "DP", "DQ", "DR", "DS", "DT", "DU", "DX",
            "GA", "GB", "GC", "GE", "GF", "GN", "GR", "GT", "GV",
            "HA", "HB", "HC", "HD", "HE", "HF", "HG", "HM", "HN", "HQ", "HS", "HT", "HV", "HX",
            "JA", "JC", "JF", "JJ", "JK", "JL", "JN", "JQ", "JS", "JV", "JX", "JZ",
            "LA", "LB", "LC", "LD", "LE", "LF", "LG", "LH", "LJ", "LT",
            "NA", "NB", "NC", "ND", "NE", "NK", "NX", "TR",
            "PA", "PE", "PB", "PC", "PD", "PF", "PG", "PH", "PJ", "PK", "PL", "PM", "PQ", "PN", "PR", "PS", "PT",
            "QA", "QB", "QC", "QD", "QE", "QH", "QK", "QL", "QM", "QP", "QR",
            "RA", "RB", "RC", "RD", "RE", "RF", "RG", "RJ", "RK", "RL", "RM", "RS", "RT", "RV", "RX", "RZ",
            "SB", "SD", "SF", "SH", "SK",
            "TA", "TC", "TD", "TE", "TF", "TG", "TH", "TJ", "TK", "TL", "TN", "TP", "TS", "TT", "TX",
            "UA", "UB", "UC", "UD", "UE", "UF", "UG", "UH", "VA", "VB", "VC", "VD", "VE", "VF", "VG", "VK", "VM", "ZA",
            "A", "Q", "S", "T", "J", "C", "D", "E", "F", "N", "Z", "H", "K", "G", "L", "U", "V", "B", "R", "M", "P"]


def get_callnumber_section(callnumber: str) -> Optional[str]:
    if not callnumber:
        raise ValueError("empty callnumber")
    for sec in SECTIONS:
        if callnumber.startswith(sec):
            return sec
    raise ValueError("invalid callnumber: %s" % callnumber)


def parse_source_file(filepath) -> Optional[Dict]:
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
                book["cn_section"] = get_callnumber_section(book["callnumber_sort"])
            except ValueError as e:
                print(book)
            books.append(book)
        posted_file["books"] = books
    return posted_file
