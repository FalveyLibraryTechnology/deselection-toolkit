import json
import progressbar
import sqlite3

from typing import Dict

from src.database_defs import *
from src.posted_files import SECTIONS
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


def loadSubjects() -> Dict:
    print("\nCreate subjects...")
    subjects = {}
    for label in open("db_data/subject_list.txt", "r"):
        cursor.execute("INSERT INTO subjects(label) VALUES (?);", (label,))
        print("\t%s: %d" % (label.strip(), cursor.lastrowid))
        subjects[label.strip()] = cursor.lastrowid
    conn.commit()
    return subjects


def loadLibrarians() -> Dict:
    print("\nCreate librarians...")
    librarians = json.load(open("db_data/librarians.json", "r"))  # librarian data by initial
    for initials in librarians:
        cursor.execute("INSERT INTO librarians(initials, name) VALUES (?,?);", (initials, librarians[initials]["name"]))
        print("\t", librarians[initials]["name"], cursor.lastrowid)
        librarians[initials]["id"] = cursor.lastrowid
    conn.commit()
    return librarians


def loadCallnumbers(librarians, subjects) -> None:
    global SECTIONS

    print("\nCreate callnumbers...")
    callnumber_counts = {}
    # Collection counts
    print("\tactive_callnumbers.txt")
    all_callnumbers = open("db_data/active_callnumbers.txt").read().split("\n")
    index = 0
    bar = progressbar.ProgressBar(max_value=len(all_callnumbers))
    for cn in all_callnumbers:
        for sec in SECTIONS:
            if cn.startswith(sec):
                if sec in callnumber_counts:
                    callnumber_counts[sec]["collection"] += 1
                else:
                    callnumber_counts[sec] = {"collection": 1, "recommended": 0}
                break
        bar.update(index)
        index += 1
    del all_callnumbers
    bar.finish()
    # Greenglass Recommendation counts
    print("\tgg_callnumbers.txt")
    gg_callnumbers = open("db_data/gg_callnumbers.txt").read().split("\n")
    index = 0
    bar = progressbar.ProgressBar(max_value=len(gg_callnumbers))
    for cn in gg_callnumbers:
        for sec in SECTIONS:
            if cn.startswith(sec):
                callnumber_counts[sec]["recommended"] += 1
                break
        gg_callnumbers[index] = normalize_callnumber(cn)
        bar.update(index)
        index += 1
    gg_callnumbers = make_unique(gg_callnumbers)
    gg_callnumbers.sort()
    open("db_data/gg_callnumbers_norm.txt", "w").write("\n".join(gg_callnumbers))
    del gg_callnumbers
    bar.finish()

    for cn_section in callnumber_counts:
        print (cn_section, callnumber_counts[cn_section])
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
        cursor.execute(
            "INSERT INTO callnumber_sections(cn_section, collection_count, gg_recommended, librarian_id) VALUES (?,?,?,?);",
            (cn_section, callnumber_counts[cn_section]["collection"], callnumber_counts[cn_section]["recommended"], assigned_to)
        )
        cursor.execute(
            "INSERT INTO sections_subjects(cn_section, subject_id) VALUES (?,?);",
            (cn_section, subject_id)
        )
    conn.commit()


def loadExcludedSets() -> None:
    print("\nLoading excluded barcodes...")
    excluded_path = "db_data/excluded"
    excluded_files = os.listdir(excluded_path)
    for file in excluded_files:
        print("\t%s" % file)
        lines = open(os.path.join(excluded_path, file), "r").read().split("\n")
        reason = lines.pop(0).strip()
        lines = make_unique(lines)
        print("\t\t%s" % reason)
        cursor.execute("INSERT INTO excluded_sets (reason) VALUES (?)", (reason,))
        set_id = cursor.lastrowid
        for barcode in lines:
            barcode = barcode.strip()
            cursor.execute("INSERT INTO excluded_barcodes (barcode, set_id) VALUES (?,?)", (barcode, set_id))
    conn.commit()


# Static data
subjects = loadSubjects()
librarians = loadLibrarians()
loadExcludedSets()
loadCallnumbers(librarians, subjects)

# Dynamic data
addNewPostedFiles(conn)
addNewRequests(conn)
updateReviewedCounts(conn)

conn.close()
