import csv
import datetime
import os
import sqlite3

from typing import List, Tuple

conn = sqlite3.connect("database.sqlite")
cursor = conn.cursor()


def writeCSVFile(filename: str, month_dir: str, columns: List[str], data: List[Tuple]) -> None:
    with open("db_reports/%s/%s" % (month_dir, filename), "w", newline="", encoding="utf8") as outfile:
        writer = csv.writer(outfile)
        writer.writerow(columns)
        writer.writerows(data)


def queryForAllFacultyRequests(file_month: datetime) -> List[Tuple]:
    cursor.execute("""
        SELECT posted_books.barcode, posted_books.callnumber, posted_books.title, posted_books.author, posted_books.pub_year, faculty.name, faculty_books.personal, faculty_requests.date
            FROM posted_books
            INNER JOIN faculty_books ON faculty_books.barcode = posted_books.barcode
            INNER JOIN faculty_requests ON faculty_requests.request_id = faculty_books.request_id
            INNER JOIN faculty ON faculty.faculty_id = faculty_requests.faculty_id
            INNER JOIN posted_files ON posted_files.file_id = posted_books.file_id
            WHERE posted_files.month = ?
            ORDER BY faculty_books.barcode ASC, faculty_requests.date ASC""", (file_month,))
    return cursor.fetchall()


def queryForAllFacultyEffective(file_month: datetime) -> List[Tuple]:
    cursor.execute("""
        SELECT posted_books.barcode, posted_books.callnumber, posted_books.title, posted_books.author, posted_books.pub_year, faculty.name, faculty_books.personal
            FROM posted_books
            INNER JOIN faculty_books ON faculty_books.barcode = posted_books.barcode
            INNER JOIN faculty_requests ON faculty_requests.request_id = faculty_books.request_id
            INNER JOIN faculty ON faculty.faculty_id = faculty_requests.faculty_id
            INNER JOIN posted_files ON posted_files.file_id = posted_books.file_id
            WHERE posted_files.month = ?
            GROUP BY faculty_books.barcode
            ORDER BY faculty_books.barcode ASC, faculty_books.personal ASC, faculty_requests.date ASC""", (file_month,))
    return cursor.fetchall()


def queryForPersonalEffective(file_month: datetime) -> List[Tuple]:
    cursor.execute("""
        SELECT posted_books.callnumber, faculty.name, faculty.address, posted_books.title, posted_books.author, posted_books.pub_year, posted_books.barcode
            FROM posted_books
            INNER JOIN faculty_books ON faculty_books.barcode = posted_books.barcode
            INNER JOIN faculty_requests ON faculty_requests.request_id = faculty_books.request_id
            INNER JOIN faculty ON faculty.faculty_id = faculty_requests.faculty_id
            INNER JOIN posted_files ON posted_files.file_id = posted_books.file_id
            WHERE posted_files.month = ?
                AND NOT EXISTS(SELECT 1 FROM faculty_books WHERE personal = 0 AND barcode = posted_books.barcode)
            GROUP BY faculty_books.barcode
            ORDER BY posted_books.callnumber_sort ASC, faculty_requests.date ASC""", (file_month,))
    return cursor.fetchall()


def queryForMasterList(file_month: datetime) -> List[Tuple]:
    cursor.execute("""
        SELECT posted_books.callnumber, posted_books.title, posted_books.author, posted_books.pub_year, posted_books.barcode
            FROM posted_books
            INNER JOIN posted_files ON posted_files.file_id = posted_books.file_id
            WHERE posted_files.month = ?
                AND NOT EXISTS(SELECT 1 FROM faculty_books WHERE barcode = posted_books.barcode)
            ORDER BY posted_books.callnumber_sort ASC""", (file_month,))
    return cursor.fetchall()


def queryForSubjectCounts() -> List[Tuple]:
    cursor.execute("""
        SELECT subjects.label, SUM(callnumber_sections.collection_count), SUM(callnumber_sections.gg_recommended), SUM(callnumber_sections.reviewed_count)
            FROM subjects
            INNER JOIN sections_subjects ON sections_subjects.subject_id = subjects.subject_id
            INNER JOIN callnumber_sections ON callnumber_sections.cn_section = sections_subjects.cn_section
            GROUP BY subjects.subject_id
            ORDER BY subjects.subject_id ASC""")
    return cursor.fetchall()


def queryForBookCounts() -> List[Tuple]:
    cursor.execute("""
        SELECT subjects.label, COUNT(posted_books.barcode), COUNT(faculty_books.barcode)
            FROM subjects
            INNER JOIN sections_subjects ON sections_subjects.subject_id = subjects.subject_id
            INNER JOIN posted_files ON posted_files.cn_section = sections_subjects.cn_section
            INNER JOIN posted_books ON posted_books.file_id = posted_files.file_id
            LEFT JOIN faculty_books ON faculty_books.barcode = posted_books.barcode
            GROUP BY subjects.subject_id
            ORDER BY subjects.subject_id ASC""")
    return cursor.fetchall()


COLLECTION_COUNT = 541277  # GG XLSX
GG_TOTAL_COUNT = 234567  # Percentage from spreadsheet


def createCollectionReview() -> None:
    global COLLECTION_COUNT, GG_TOTAL_COUNT

    outfile = open("db_reports/collection_review.csv", "w", encoding="utf-8")
    subject_counts = queryForSubjectCounts()
    book_counts = queryForBookCounts()
    as_of = datetime.datetime.strftime(datetime.datetime.now(), "%m/%d")
    outfile.write("Print Monograph Collection Review\n")
    outfile.write(
        "Subject Area,# of Items in Subject Area,% of Total Collection,% of Total Monograph Collection (print & electonic),," +
        "# of Items in Subject Area Identified for Review by Greenglass,% of Subject Area Identified for Review by Greenglass,," +
        "# of Items Reviewed In Subject Area (as of %s),%% of Identified Items Reviewed in Subject Area (as of %s)," % (
        as_of, as_of) +
        "# of Reviewed Items Retained by Librarians (as of %s),%% of Reviewed Items Retained by Librarians\n" % as_of)
    index = 0
    for subject in subject_counts:
        label, collection_count, gg_recommended, reviewed_count = subject
        label, posted_counts, faculty_count = book_counts[index]
        librarian_retained = reviewed_count - posted_counts
        outfile.write(
            "%s,%d,%.5f,,,%d,%.5f,,%d,%.5f,%d,%.5f\n" % (
                label.strip(), collection_count, collection_count / COLLECTION_COUNT,
                gg_recommended, gg_recommended / GG_TOTAL_COUNT,
                reviewed_count, reviewed_count / gg_recommended, librarian_retained, librarian_retained / reviewed_count
            )
        )
        index += 1
    outfile.write(
        "\n\n\nSubject Area,# of Items in Subject Area,% of Total  Collection,% of Total Monograph Collection (print & electonic),," +
        "# of Items in Subject Area to be Retained (as of %s),# of Items in Subject Area Remaining to be Reviewed (as of %s),," % (
        as_of, as_of) +
        "%% of Items in Subject Area to be Retained (as of %s)\n" % as_of)
    index = 0
    for subject in subject_counts:
        label, collection_count, gg_recommended, reviewed_count = subject
        label, posted_counts, faculty_count = book_counts[index]
        librarian_retained = reviewed_count - posted_counts
        outfile.write(
            "%s,%d,%.5f,,,%d,%d,,%.5f\n" % (
                label.strip(), collection_count, collection_count / COLLECTION_COUNT,
                collection_count - (gg_recommended - librarian_retained - faculty_count),
                gg_recommended - reviewed_count,
                (collection_count - (gg_recommended - librarian_retained - faculty_count)) / collection_count,
            )
        )
        index += 1


months = [dir_.path.split("/")[1] for dir_ in os.scandir("sources/") if dir_.is_dir()]
for month in months:
    print("\t%s" % month)
    month_date = datetime.datetime.strptime(month, "%B %Y")
    if not os.path.exists("db_reports/%s/" % month):
        os.mkdir("db_reports/%s/" % month)
    # Faculty All Requests
    writeCSVFile(
        "faculty-all-requests.csv", month,
        ["Barcode", "Callnumber", "Title", "Author", "Publish Year", "Faculty Name", "Personal", "Request Date"],
        queryForAllFacultyRequests(month_date)
    )
    # Faculty Effective
    writeCSVFile(
        "faculty-effective-requests.csv", month,
        ["Barcode", "Callnumber", "Title", "Author", "Publish Year", "Faculty Name", "Personal"],
        queryForAllFacultyEffective(month_date)
    )
    # Personal Retention Effective
    writeCSVFile(
        "faculty-requests-for-personal-collections.csv", month,
        ["Callnumber", "Faculty Name", "Faculty Address", "Title", "Author", "Publish Year", "Barcode"],
        queryForPersonalEffective(month_date)
    )
    # Master Pull List
    writeCSVFile(
        "master-pull-list.csv", month,
        ["Callnumber", "Title", "Author", "Publish Year", "Barcode"],
        queryForMasterList(month_date)
    )

createCollectionReview()
