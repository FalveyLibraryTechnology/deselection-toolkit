import json
import os
import re
import sqlite3
import datetime # must be after sqlite3

from src.posted_files import parse_source_dir, SECTIONS
from src.utils import make_unique, normalize_callnumber

# Check if exists
if os.path.exists("database.sqlite"):
    os.remove("database.sqlite") # debug
    # print ("database.sqlite already exists")
    # exit(0)

# Make and Reset database
init_sql = open("db_data/init.sql", "r").read()
conn = sqlite3.connect("database.sqlite")
cursor = conn.cursor()
cursor.executescript(init_sql)
conn.commit()

def loadSubjects():
    print ("Create subjects...")
    subjects = {}
    for label in open("db_data/subject_list.txt", "r"):
        cursor.execute("INSERT INTO subjects(label) VALUES (?);", (label, ))
        print ("\t%s: %d" % (label.strip(), cursor.lastrowid))
        subjects[label.strip()] = cursor.lastrowid
    conn.commit()
    return subjects

def loadLibrarians():
    print ("\nCreate librarians...")
    librarians = json.load(open("db_data/librarians.json", "r")) # librarian data by initial
    for initials in librarians:
        cursor.execute("INSERT INTO librarians(initials, name) VALUES (?,?);", (initials, librarians[initials]["name"]))
        print ("\t", librarians[initials]["name"], cursor.lastrowid)
        librarians[initials]["id"] = cursor.lastrowid
    conn.commit()
    return librarians

def loadCallnumbers(librarians, subjects):
    global SECTIONS

    print ("\nCreate callnumbers...")
    callnumber_counts = {}
    # Collection counts
    print ("\tactive_callnumbers.txt")
    all_callnumbers = open("db_data/active_callnumbers.txt").read().split("\n")
    index = 0
    for cn in all_callnumbers:
        for sec in SECTIONS:
            if cn.startswith(sec):
                if sec in callnumber_counts:
                    callnumber_counts[sec]["collection"] += 1
                else:
                    callnumber_counts[sec] = { "collection": 1, "recommended": 0 }
                break
        # Save normalized for later
        '''
        all_callnumbers[index] = normalize_callnumber(cn)
        index += 1
    active_callnumbers = make_unique(all_callnumbers)
    active_callnumbers.sort()
    open("db_data/active_callnumbers_norm.txt", "w").write("\n".join(active_callnumbers))
    '''
    del all_callnumbers
    # Greenglass Recommendation counts
    print ("\tgg_callnumbers.txt")
    gg_callnumbers = open("db_data/gg_callnumbers.txt").read().split("\n")
    index = 0
    for cn in gg_callnumbers:
        for sec in SECTIONS:
            if cn.startswith(sec):
                callnumber_counts[sec]["recommended"] += 1
                break
        gg_callnumbers[index] = normalize_callnumber(cn)
        index += 1
    gg_callnumbers = make_unique(gg_callnumbers)
    gg_callnumbers.sort()
    open("db_data/gg_callnumbers_norm.txt", "w").write("\n".join(gg_callnumbers))
    del gg_callnumbers

    for section in callnumber_counts:
        # print ("\t%s: %d / %d" % (section, callnumber_counts[section]["recommended"], callnumber_counts[section]["collection"]))
        subject = -1
        assigned_to = -1
        for initials in librarians:
            if section in librarians[initials]["assignment"]:
                subject = subjects[librarians[initials]["subject"]]
                assigned_to = librarians[initials]["id"]
        if subject == -1:
            print ("missing", section)
            break
        cursor.execute(
            "INSERT INTO callnumber_sections(cn_section, collection_count, gg_recommended, subject_id, librarian_id) VALUES (?,?,?,?,?);",
            (section, callnumber_counts[section]["collection"], callnumber_counts[section]["recommended"], subject, assigned_to)
        )
    conn.commit()

def loadExcludedSets():
    print ("\nLoading excluded barcodes...")
    excluded_path = "db_data/excluded"
    excluded_files = os.listdir(excluded_path)
    for file in excluded_files:
        print ("\t%s" % file)
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

def loadPostedFiles(librarians):
    print ("\nLoading Posted Files...")
    weeding_dirs = [dir.path for dir in os.scandir("sources/") if dir.is_dir()]
    for dir in weeding_dirs:
        month = dir.split("/")[1]
        print ("\t%s" % month)
        month_files = parse_source_dir(dir)
        for file in month_files:
            file_id = -1
            for initials in librarians:
                if ("_%s_" % initials) in file["name"]:
                    month_date = datetime.datetime.strptime(month, "%B %Y")
                    cursor.execute(
                        "INSERT INTO posted_files (name, cn_section, librarian_id, month) VALUES (?,?,?,?)",
                        (file["name"], file["cn_section"], librarians[initials]["id"], month_date)
                    )
                    file_id = cursor.lastrowid
                    break
            for book in file["books"]:
                cursor.execute(
                    "INSERT INTO posted_books (barcode, callnumber, callnumber_sort, title, author, pub_year, file_id) VALUES (?,?,?,?,?,?,?)",
                    (int(book["barcode"]), book["callnumber"], book["callnumber_sort"], book["title"], book["author"], book["year"], file_id)
                )
    conn.commit()

subjects = loadSubjects()
librarians = loadLibrarians()
loadExcludedSets()
loadPostedFiles(librarians)
loadCallnumbers(librarians, subjects)

conn.close()
