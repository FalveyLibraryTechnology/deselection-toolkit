import json
import progressbar
import sqlite3

from typing import Dict

from src.database_defs import *
from src.posted_files import get_callnumber_section
from src.utils import make_unique, normalize_callnumber

# Check if exists
if os.path.exists("database.sqlite"):
    os.remove("database.sqlite")  # debug

# Make and Reset database
init_sql = open("db_data/init.sql", "r").read()
conn = sqlite3.connect("database.sqlite")
cursor = conn.cursor()
cursor.executescript(init_sql)
conn.commit()


def load_subjects() -> Dict:
    print("\nCreate subjects...")
    subjects = {}
    for label in open("db_data/subject_list.txt", "r", encoding="utf-8"):
        cursor.execute("INSERT INTO subjects(label) VALUES (?);", (label,))
        print("\t%s: %d" % (label.strip(), cursor.lastrowid))
        subjects[label.strip()] = cursor.lastrowid
    conn.commit()
    return subjects


def load_librarians() -> Dict:
    print("\nCreate librarians...")
    # librarian data by initial
    librarians = json.load(
        open("db_data/librarians.json", "r", encoding="utf-8"))
    for initials in librarians:
        cursor.execute("INSERT INTO librarians(initials, name) VALUES (?,?);",
                       (initials, librarians[initials]["name"]))
        print("\t", librarians[initials]["name"], cursor.lastrowid)
        librarians[initials]["id"] = cursor.lastrowid
        for assignment in librarians[initials]["assignment"]:
            cursor.execute(
                "INSERT INTO librarian_assignments(cn_section, librarian_id) VALUES (?,?);",
                (assignment, librarians[initials]["id"])
            )
    conn.commit()
    return librarians


def load_callnumbers(librarians, subjects) -> None:
    print("\nCreate callnumbers...")
    callnumber_counts = {}

    # Collection counts
    print("\tactive_callnumbers.txt")
    all_callnumbers = open("db_data/active_callnumbers.txt",
                           encoding="utf-8").read().split("\n")
    index = 0
    bar = progressbar.ProgressBar(max_value=len(all_callnumbers))
    for cn in all_callnumbers:
        try:
            sec = get_callnumber_section(cn)
            if sec in callnumber_counts:
                callnumber_counts[sec]["collection"] += 1
            else:
                callnumber_counts[sec] = {"collection": 1, "recommended": 0}
        except ValueError:
            pass
        bar.update(index)
        index += 1
    del all_callnumbers
    bar.finish()

    # Normalize callnumbers
    print("\tnormalize gg_callnumbers.txt")
    gg_callnumbers = open("db_data/gg_callnumbers.txt",
                          encoding="utf-8").read().split("\n")
    bar = progressbar.ProgressBar(max_value=len(gg_callnumbers))
    index = 0
    for cn in gg_callnumbers:
        gg_callnumbers[index] = normalize_callnumber(cn)
        bar.update(index)
        index += 1
    bar.finish()
    open("db_data/gg_callnumbers_norm.txt", "w",
         encoding="utf-8").write("\n".join(gg_callnumbers))
    del gg_callnumbers

    # Load GG counts
    gg_counts = json.load(open("db_data/gg_section_counts.json", "r"))
    for cn in gg_counts:
        cn_section = cn
        try:
            cn_section = get_callnumber_section(cn)
        except:
            continue
        callnumber_counts[cn_section]["recommended"] += gg_counts[cn] if cn in gg_counts else 0

    # Insert
    for cn_section in callnumber_counts:
        subject_id = -1
        assigned_to = -1
        for initials in librarians:
            if cn_section in librarians[initials]["assignment"]:
                subject_id = subjects[librarians[initials]["subject"]]
                assigned_to = librarians[initials]["id"]
                break
        if subject_id == -1:
            print("missing", cn_section)
            break
        section = callnumber_counts[cn_section]
        # GG counts may be higher due to collection changes
        if section["collection"] < section["recommended"]:
            section["collection"] = section["recommended"]
        cursor.execute(
            "INSERT INTO callnumber_sections"
            "(cn_section, collection_count, gg_recommended, reviewed_count, librarian_id) VALUES (?,?,?,?,?);",
            (cn_section, section["collection"],
             section["recommended"], 0, assigned_to)
        )
        cursor.execute(
            "INSERT INTO sections_subjects(cn_section, subject_id) VALUES (?,?);",
            (cn_section, subject_id)
        )
    conn.commit()


def load_excluded_sets() -> None:
    print("\nLoading excluded barcodes...")
    excluded_path = "db_data/excluded"
    excluded_files = os.listdir(excluded_path)
    for file in excluded_files:
        print("\t%s" % file)
        lines = open(os.path.join(excluded_path, file), "r",
                     encoding="utf-8").read().split("\n")
        reason = lines.pop(0).strip()
        lines = make_unique(lines)
        print("\t\t%s" % reason)
        cursor.execute(
            "INSERT INTO excluded_sets (reason) VALUES (?)", (reason,))
        set_id = cursor.lastrowid
        for barcode in lines:
            barcode = barcode.strip()
            cursor.execute(
                "INSERT INTO excluded_barcodes (barcode, set_id) VALUES (?,?)", (barcode, set_id))
    conn.commit()


# Static data
SUBJECTS = load_subjects()
LIBRARIANS = load_librarians()
load_excluded_sets()
load_callnumbers(LIBRARIANS, SUBJECTS)

# Dynamic data
addNewPostedFiles(conn)
addNewRequests(conn)
updateReviewedCounts(conn)

conn.close()
