from math import floor
import progressbar
import re
from string import ascii_uppercase
from xlrd import open_workbook  # Excel files
import xlwings as xw
from xlwings.constants import DeleteShiftDirection

BAR_WIDGETS = [
    "\t", progressbar.SimpleProgress(), " ",
    progressbar.Bar(), " ",
    progressbar.DynamicMessage("affected"), " | ",
    progressbar.AdaptiveETA()
]


def get_column_letter(number):
    letter = ascii_uppercase[number % 26]
    if (number >= 26):
        letter = get_column_letter(floor(number / 26) - 1) + letter
    return letter


# func returns True for keep, False for remove
def excel_filter_rows(filepath, output, row_func):
    print("\nopening %s to remove rows..." % filepath)
    wb = xw.Book(filepath)
    wb.app.visible = False
    sheet = wb.sheets[0]
    progress = 1
    removed = 0
    rownum = sheet.range('A1').current_region.last_cell.row
    bar = progressbar.ProgressBar(max_value=rownum, widgets=BAR_WIDGETS)
    for row in range(rownum, 1, -1):
        values = sheet.range("%d:%d" % (row, row)).value
        if not row_func(values, progress):
            sheet.range("%d:%d" % (row, row)).api.Delete(DeleteShiftDirection.xlShiftUp)
            removed += 1
        progress += 1
        bar.update(progress, affected=removed)
    bar.finish()
    wb.save(output)
    print("\tsaved to %s..." % output)
    wb.app.kill()


# row_func returns True to highlight
def excel_highlight_rows(filepath, output, row_func, hcolor=(255, 255, 0)):
    print("\nopening %s to highlight rows..." % filepath)
    wb = xw.Book(filepath)
    wb.app.visible = False
    sheet = wb.sheets[0]
    progress = 1
    highlighted = 0
    rownum = sheet.range('A1').current_region.last_cell.row
    bar = progressbar.ProgressBar(max_value=rownum, widgets=BAR_WIDGETS)
    for row in range(rownum, 1, -1):
        values = sheet.range("%d:%d" % (row, row)).value
        if row_func(values, progress):
            sheet.range("%d:%d" % (row, row)).color = hcolor
            highlighted += 1
        progress += 1
        bar.update(progress, affected=highlighted)
    bar.finish()
    wb.save(output)
    print("\tsaved to %s..." % output)
    wb.app.kill()


'''
def excel_insert_column(filepath, output, column_index, data, start_row=0):
    print("\nadding column to %s..." % filepath)
    wb = xw.Book(filepath)
    wb.app.visible = False
    sheet = wb.sheets[0]
    ...
    bar.finish()
    wb.save(output)
    print("\tsaved to %s..." % output)
    wb.app.kill()
'''


def get_excel_column_by_regex(column_re, filepath):
    rows = []
    pattern = re.compile(column_re)
    with open_workbook(filepath) as book:
        for s in range(book.nsheets):
            sheet = book.sheet_by_index(s)
            columns = {}
            body = False
            row_index = 1
            for row in range(0, sheet.nrows):
                rvalues = sheet.row_values(row)
                if not body:
                    for col in rvalues:
                        if not col:
                            continue
                        if pattern.search(str(col)):
                            columns[col] = rvalues.index(col)
                            body = True
                else:
                    row = {"_number": row_index}
                    for col in columns:
                        row[col] = rvalues[columns[col]]
                    rows.append(row)
                row_index += 1
    return rows
