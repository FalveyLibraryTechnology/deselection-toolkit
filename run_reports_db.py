import csv
import datetime
import os
import sqlite3

from typing import Dict, List, Tuple

conn = sqlite3.connect("database.sqlite")
cursor = conn.cursor()


def write_csv_file(filename: str, month_dir: str, columns: List[str], data: List[Tuple]) -> None:
    with open("db_reports/%s/%s" % (month_dir, filename), "w", newline="", encoding="utf8") as outfile:
        writer = csv.writer(outfile)
        writer.writerow(columns)
        writer.writerows(data)


def query_all_faculty_requests(file_month: datetime) -> List[Tuple]:
    where_conjunction = "AND" if file_month else "OR"  # OR for all months
    cursor.execute("""
        SELECT posted_books.barcode, posted_books.callnumber, posted_books.title, posted_books.author, 
               posted_books.pub_year, faculty.name, faculty_books.personal, faculty_requests.date
            FROM posted_books
            INNER JOIN faculty_books ON faculty_books.barcode = posted_books.barcode
            INNER JOIN faculty_requests ON faculty_requests.request_id = faculty_books.request_id
            INNER JOIN faculty ON faculty.faculty_id = faculty_requests.faculty_id
            INNER JOIN posted_files ON posted_files.file_id = posted_books.file_id
            WHERE posted_files.month IS NOT NULL %s posted_files.month = ?
            ORDER BY faculty_books.barcode ASC, faculty_requests.date ASC""" % where_conjunction,
                   (file_month,))
    return cursor.fetchall()


def query_faculty_effective(file_month: datetime) -> List[Tuple]:
    where_conj = "AND" if file_month else "OR"  # OR for all months
    cursor.execute("""
        SELECT posted_books.barcode, posted_books.callnumber, posted_books.title, posted_books.author, 
               posted_books.pub_year, faculty.name, faculty_books.personal
            FROM posted_books
            INNER JOIN faculty_books ON faculty_books.barcode = posted_books.barcode
            INNER JOIN faculty_requests ON faculty_requests.request_id = faculty_books.request_id
            INNER JOIN faculty ON faculty.faculty_id = faculty_requests.faculty_id
            INNER JOIN posted_files ON posted_files.file_id = posted_books.file_id
            WHERE posted_files.month IS NOT NULL %s posted_files.month = ?
            GROUP BY faculty_books.barcode
            ORDER BY faculty_books.barcode ASC, faculty_books.personal ASC, faculty_requests.date ASC""" % where_conj,
                   (file_month,))
    return cursor.fetchall()


def query_for_personal_effective(file_month: datetime) -> List[Tuple]:
    where_conjunction = "AND" if file_month else "OR"  # OR for all months
    cursor.execute("""
        SELECT posted_books.callnumber, faculty.name, faculty.address, posted_books.title, posted_books.author, 
               posted_books.pub_year, posted_books.barcode
            FROM posted_books
            INNER JOIN faculty_books ON faculty_books.barcode = posted_books.barcode
            INNER JOIN faculty_requests ON faculty_requests.request_id = faculty_books.request_id
            INNER JOIN faculty ON faculty.faculty_id = faculty_requests.faculty_id
            INNER JOIN posted_files ON posted_files.file_id = posted_books.file_id
            WHERE (posted_files.month IS NOT NULL %s posted_files.month = ?)
                AND NOT EXISTS(SELECT 1 FROM faculty_books WHERE personal = 0 AND barcode = posted_books.barcode)
            GROUP BY faculty_books.barcode
            ORDER BY posted_books.callnumber_sort ASC, faculty_requests.date ASC""" % where_conjunction,
                   (file_month,))
    return cursor.fetchall()


def query_master_list(file_month: datetime) -> List[Tuple]:
    cursor.execute("""
        SELECT posted_books.callnumber, posted_books.title, posted_books.author, posted_books.pub_year, 
               posted_books.barcode
            FROM posted_books
            INNER JOIN posted_files ON posted_files.file_id = posted_books.file_id
            WHERE posted_files.month = ?
                AND NOT EXISTS(SELECT 1 FROM faculty_books WHERE barcode = posted_books.barcode)
            ORDER BY posted_books.callnumber_sort ASC""", (file_month,))
    return cursor.fetchall()


def query_subject_counts() -> List[Tuple]:
    cursor.execute("""
        SELECT subjects.label, SUM(callnumber_sections.collection_count), SUM(callnumber_sections.gg_recommended), 
               SUM(callnumber_sections.reviewed_count)
            FROM subjects
            INNER JOIN sections_subjects ON sections_subjects.subject_id = subjects.subject_id
            INNER JOIN callnumber_sections ON callnumber_sections.cn_section = sections_subjects.cn_section
            GROUP BY subjects.subject_id
            ORDER BY subjects.subject_id ASC""")
    return cursor.fetchall()


def query_subject_book_counts() -> List[Tuple]:
    cursor.execute("""
        SELECT subjects.label, COUNT(posted_books.barcode), COUNT(faculty_books.barcode)
            FROM subjects
            INNER JOIN sections_subjects ON sections_subjects.subject_id = subjects.subject_id
            INNER JOIN posted_books ON posted_books.cn_section = sections_subjects.cn_section
            LEFT JOIN faculty_books ON faculty_books.barcode = posted_books.barcode
            GROUP BY subjects.subject_id
            ORDER BY subjects.subject_id ASC""")
    return cursor.fetchall()


def query_section_counts() -> List[Tuple]:
    cursor.execute("""
        SELECT cn_section, SUM(collection_count), SUM(gg_recommended), SUM(reviewed_count)
            FROM callnumber_sections
            GROUP BY cn_section
            ORDER BY cn_section ASC""")
    return cursor.fetchall()


def query_section_book_counts() -> List[Tuple]:
    cursor.execute("""
        SELECT callnumber_sections.cn_section, COUNT(posted_books.barcode)
            FROM callnumber_sections
            INNER JOIN posted_books ON posted_books.cn_section = callnumber_sections.cn_section
            GROUP BY callnumber_sections.cn_section
            ORDER BY callnumber_sections.cn_section ASC""")
    return cursor.fetchall()


def get_cumulative_effective_bysection() -> Dict:
    cursor.execute("""
        SELECT callnumber_sections.cn_section
            FROM callnumber_sections
            INNER JOIN posted_books ON posted_books.cn_section = callnumber_sections.cn_section
            INNER JOIN faculty_books ON faculty_books.barcode = posted_books.barcode
            INNER JOIN faculty_requests ON faculty_requests.request_id = faculty_books.request_id
            INNER JOIN faculty ON faculty.faculty_id = faculty_requests.faculty_id
            GROUP BY faculty_books.barcode
            ORDER BY faculty_books.barcode ASC, faculty_books.personal ASC, faculty_requests.date ASC""")
    counts = {}
    for row in cursor.fetchall():
        section = row[0]
        if section in counts:
            counts[section] += 1
        else:
            counts[section] = 1
    return counts


def get_cumulative_personal_bysection() -> Dict[str, int]:
    cursor.execute("""
        SELECT callnumber_sections.cn_section
            FROM callnumber_sections
            INNER JOIN posted_books ON posted_books.cn_section = callnumber_sections.cn_section
            INNER JOIN faculty_books ON faculty_books.barcode = posted_books.barcode
            INNER JOIN faculty_requests ON faculty_requests.request_id = faculty_books.request_id
            INNER JOIN faculty ON faculty.faculty_id = faculty_requests.faculty_id
            WHERE NOT EXISTS(SELECT 1 FROM faculty_books WHERE personal = 0 AND barcode = posted_books.barcode)
            GROUP BY faculty_books.barcode
            ORDER BY posted_books.callnumber_sort ASC, faculty_requests.date ASC""")
    counts = {}
    for row in cursor.fetchall():
        section = row[0]
        if section in counts:
            counts[section] += 1
        else:
            counts[section] = 1
    return counts


def generate_reports_for_period(folder: str, query_date: datetime) -> None:
    if not os.path.exists("db_reports/%s/" % folder):
        os.mkdir("db_reports/%s/" % folder)
    # Faculty All Requests
    write_csv_file(
        "faculty-all-requests.csv", folder,
        ["Barcode", "Callnumber", "Title", "Author", "Publish Year", "Faculty Name", "Personal", "Request Date"],
        query_all_faculty_requests(query_date)
    )
    # Faculty Effective
    write_csv_file(
        "faculty-effective-requests.csv", folder,
        ["Barcode", "Callnumber", "Title", "Author", "Publish Year", "Faculty Name", "Personal"],
        query_faculty_effective(query_date)
    )
    # Personal Retention Effective
    write_csv_file(
        "faculty-requests-for-personal-collections.csv", folder,
        ["Callnumber", "Faculty Name", "Faculty Address", "Title", "Author", "Publish Year", "Barcode"],
        query_for_personal_effective(query_date)
    )
    if query_date is not None:
        # Master Pull List
        write_csv_file(
            "master-pull-list.csv", folder,
            ["Callnumber", "Title", "Author", "Publish Year", "Barcode"],
            query_master_list(query_date)
        )


def create_collection_review() -> None:
    print("Create Collection Review (MG Format)...")
    subject_counts = query_subject_counts()

    collection_total = 0
    for subject in subject_counts:
        label, collection_count, gg_recommended, reviewed_count = subject
        collection_total += collection_count

    outfile = open("db_reports/collection_review.csv", "w", encoding="utf-8")
    book_counts = query_subject_book_counts()
    as_of = datetime.datetime.strftime(datetime.datetime.now(), "%m/%d")
    outfile.write("Print Monograph Collection Review\n"
                  "Subject Area,# of Items in Subject Area,% of Total Collection,"
                  "% of Total Monograph Collection (print & electonic),,"
                  '# of Items in Subject Area Identified for Review by Greenglass,'
                  "% of Subject Area Identified for Review by Greenglass,,"
                  "# of Items Reviewed In Subject Area (as of %s),"
                  "%% of Identified Items Reviewed in Subject Area (as of %s),"
                  "# of Reviewed Items Retained by Librarians (as of %s),"
                  "%% of Reviewed Items Retained by Librarians\n".format(as_of, as_of, as_of))
    index = 0
    for subject in subject_counts:
        label, collection_count, gg_recommended, reviewed_count = subject
        label, posted_counts, faculty_count = book_counts[index]
        librarian_retained = reviewed_count - posted_counts
        outfile.write(
            "%s,%d,%.5f,,,%d,%.5f,,%d,%.5f,%d,%.5f\n" % (
                label.strip(), collection_count, collection_count / collection_total,
                gg_recommended, gg_recommended / collection_count,
                reviewed_count, reviewed_count / gg_recommended, librarian_retained, librarian_retained / reviewed_count
            )
        )
        index += 1
        outfile.write("\n\n\n")
        outfile.write("Subject Area,# of Items in Subject Area,"
                      "% of Total Collection,"
                      "% of Total Monograph Collection (print & electonic),,"
                      "# of Items in Subject Area to be Retained (as of %s),"
                      "# of Items in Subject Area Remaining to be Reviewed (as of %s),,"
                      "%% of Items in Subject Area to be Retained (as of %s)\n".format(as_of, as_of, as_of))

    index = 0
    for subject in subject_counts:
        label, collection_count, gg_recommended, reviewed_count = subject
        label, posted_counts, faculty_count = book_counts[index]
        librarian_retained = reviewed_count - posted_counts
        outfile.write(
            "%s,%d,%.5f,,,%d,%d,,%.5f\n" % (
                label.strip(), collection_count, collection_count / collection_total,
                collection_count - (gg_recommended - librarian_retained - faculty_count),
                gg_recommended - reviewed_count,
                (collection_count - (gg_recommended - librarian_retained - faculty_count)) / collection_count,
            )
        )
        index += 1


def progress_by_callnumber_section() -> None:
    print("Create Progress By Callnumber Table...")
    section_counts = query_section_counts()
    book_counts = query_section_book_counts()
    faculty_counts = get_cumulative_effective_bysection()
    personal_counts = get_cumulative_personal_bysection()

    collection_total = 0
    gg_rec_total = 0
    for section in section_counts:
        label, collection_count, gg_recommended, reviewed_count = section
        collection_total += collection_count
        gg_rec_total += gg_recommended

    cn_section_rows = []
    missing_book_counts = 0
    for index in range(len(section_counts)):
        label, collection_count, gg_recommended, reviewed_count = section_counts[index]
        bc_label, posted_counts = book_counts[index - missing_book_counts]
        if label != bc_label:
            posted_counts = 0
            missing_book_counts += 1
        faculty_count = faculty_counts[label] if label in faculty_counts else 0
        personal_count = personal_counts[label] if label in personal_counts else 0
        cn_section_rows.append((
            label,  # section
            collection_count,  # items in collection
            collection_count / collection_total,  # percentage of collection
            gg_recommended,  # items recommended
            gg_recommended / collection_count,  # percentage of collection recommended
            reviewed_count,  # items reviews by librarians
            reviewed_count / gg_recommended if gg_recommended > 0 else 0,  # percentage of gg librarian reviewed
            reviewed_count - posted_counts,  # items retained by staff
            ((reviewed_count - posted_counts) / gg_recommended) if gg_recommended > 0 else 0,  # % librarian retained
            posted_counts,  # items posted to faculty
            faculty_count,  # items retained in collection by faculty
            personal_count,  # faculty personal collections
            (faculty_count / posted_counts) if posted_counts > 0 else "",  # percentage of posted retained by faculty
            (faculty_count / gg_recommended) if posted_counts > 0 else 0  # percentage of recommended faculty retained
        ))
    write_csv_file(
        "callnumber_section_stats.csv", ".",
        ["Callnumber Section", "# of Items in Collection", "Percentage of Collection",
         "# of Items Recommended for Removal by Greenglass", "% of Collection Quantitatively Recommended For Removal",
         "# of Items Reviewed By Library Staff", "% of Recommendations Reviewed To Date (Progress)",
         "# of Items Retained by Library Staff", "% of Recommendations Retained By Library Staff",
         "# of Items Posted to Faculty", "# of Items Retained In Collection By Faculty",
         "# of Items Requested For Personal Collections By Faculty", "% of Posted Items Retained By Faculty",
         "% of Recommendations Retained by Faculty"],
        cn_section_rows
    )


print("Create Monthly Data Reports...")
months = [dir_.path.split("/")[1] for dir_ in os.scandir("sources/") if dir_.is_dir()]
for month in months:
    print("\t%s" % month)
    month_date = datetime.datetime.strptime(month, "%B %Y")
    generate_reports_for_period(month, month_date)

print("Create Cumulative Reports...")
generate_reports_for_period("Cumulative", None)
create_collection_review()
progress_by_callnumber_section()
