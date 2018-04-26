import json
import os
import re
import sqlite3

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
    print ("\nCreate callnumbers...")
    sections = []
    for initials in librarians:
        sections.extend(librarians[initials]["assignment"])
    sections.sort(key=lambda s: len(s), reverse=True) # longest first
    callnumber_counts = {}
    # Collection counts
    print ("\tactive_callnumbers.txt")
    all_callnumbers = open("db_data/active_callnumbers.txt").read().split("\n")
    for cn in all_callnumbers:
        if cn.startswith(sec):
            if sec in callnumber_counts:
                callnumber_counts[sec]["collection"] += 1
            else:
                callnumber_counts[sec] = { "collection": 1, "recommended": 0 }
            break
    del all_callnumbers
    # Greenglass Recommendation counts
    print ("\tgg_callnumbers.txt")
    gg_callnumbers = open("db_data/gg_callnumbers.txt").read().split("\n")
    for cn in gg_callnumbers:
        if cn.startswith(sec):
            callnumber_counts[sec]["recommended"] += 1
            break
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
            "INSERT INTO callnumber_sections(section, collection_count, gg_recommended, subject, assigned_to) VALUES (?,?,?,?,?);",
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
        print("\t\t%s" % reason)
        cursor.execute("INSERT INTO excluded_sets (reason) VALUES (?)", (reason,))
        set_id = cursor.lastrowid
        for barcode in lines:
            barcode = barcode.strip()
            cursor.execute("INSERT INTO excluded_barcodes (barcode, set_id) VALUES (?,?)", (barcode, set_id))
    conn.commit()

subjects = loadSubjects()
librarians = loadLibrarians()
loadCallnumbers(librarians, subjects)
loadExcludedSets()

conn.close()
