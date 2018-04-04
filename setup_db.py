import json
import os
import sqlite3

# Check if exists
if os.path.exists("database.sql"):
    os.remove("database.sql") # debug
    # print ("database.sql already exists")
    # exit(0)

# Make database
conn = sqlite3.connect("database.sql")
cursor = conn.cursor()

# Create set tables

print ("Create subjects...")
# TODO: Make external
subjects = {
    "STEM": -1,
    "Humanities": -1,
    "Social Sciences": -1,
}
cursor.execute("""CREATE TABLE subjects
                    (id integer primary key autoincrement, label varchar);""")
for label in subjects:
    cursor.execute("INSERT INTO subjects(label) VALUES (?);", (label, ))
    print ("\t", label, cursor.lastrowid)
    subjects[label] = cursor.lastrowid
conn.commit()

print ("Create librarians...")
cursor.execute("""CREATE TABLE librarians
                    (id integer primary key autoincrement, name varchar unique, initials varchar unique);""")
librarians = json.load(open("db_data/librarians.json", "r")) # librarian data by initial
for initials in librarians:
    cursor.execute("INSERT INTO librarians(initials, name) VALUES (?,?);", (initials, librarians[initials]["name"]))
    print ("\t", librarians[initials]["name"], cursor.lastrowid)
    librarians[initials]["id"] = cursor.lastrowid
conn.commit()

print ("Create callnumbers...")
cursor.execute("""CREATE TABLE callnumbers
                    (section varchar primary key, assigned_to integer, subject integer,
                     collection_total integer, gg_recommended integer, reviewed_count integer, posted_count integer);""")
callnumbers = json.load(open("db_data/callnumbers.json", "r")) # callnumbers data by section
callnumbers_sorted = [key for key in callnumbers]
callnumbers_sorted.sort()
for section in callnumbers_sorted:
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
        "INSERT INTO callnumbers(section, collection_total, gg_recommended, subject, assigned_to) VALUES (?,?,?,?,?);",
        (section, callnumbers[section]["collection"], callnumbers[section]["gg_total"], subject, assigned_to)
    )
    print ("\t", section, cursor.lastrowid, assigned_to)
conn.commit()

# - Create tables to be populated by other scriptscursor.execute("CREATE TABLE excluded (barcode integer primary key, reason text);")
cursor.execute("""CREATE TABLE faculty
                    (id integer primary key autoincrement, name varchar unique, department varchar, address varchar, email varchar);""")
cursor.execute("""CREATE TABLE faculty_requests
                    (id integer primary key autoincrement, date timestamp, faculty integer);""")
cursor.execute("""CREATE TABLE book_requests
                    (id integer primary key autoincrement, barcode integer, cn_section varchar,
                     request integer, personal boolean, comment text, from_file integer);""")
cursor.execute("""CREATE TABLE posted_files
                    (id integer primary key autoincrement, name varchar, created_by integer, item_count integer);""")
conn.commit()

conn.close()
