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
librarians = json.load(open("setup_data/librarians.json", "r")) # librarian data by initial
for initials in librarians:
    cursor.execute("INSERT INTO librarians(initials, name) VALUES (?,?);", (initials, librarians[initials]["name"]))
    print ("\t", librarians[initials]["name"], cursor.lastrowid)
    librarians[initials]["id"] = cursor.lastrowid
conn.commit()

print ("Create callnumbers...")
cursor.execute("""CREATE TABLE callnumbers
                    (section varchar primary key, collection_total integer, gg_recommended integer, category integer, assigned_to integer);""")
callnumbers = json.load(open("setup_data/callnumbers.json", "r")) # callnumbers data by section
callnumbers_sorted = [key for key in callnumbers]
callnumbers_sorted.sort()
for section in callnumbers_sorted:
    category = -1
    assigned_to = -1
    for initials in librarians:
        if section in librarians[initials]["assignment"]:
            category = subjects[librarians[initials]["subject"]]
            assigned_to = librarians[initials]["id"]
    if category == -1:
        print ("missing", section)
        break
    cursor.execute(
        "INSERT INTO callnumbers(section, collection_total, gg_recommended, category, assigned_to) VALUES (?,?,?,?,?);",
        (section, callnumbers[section]["collection"], callnumbers[section]["gg_total"], category, assigned_to)
    )
    print ("\t", section, cursor.lastrowid, assigned_to)
conn.commit()


# - Create tables to be populated by other scriptscursor.execute("""CREATE TABLE faculty
                    (id integer primary key autoincrement, name varchar unique, location varchar, department varchar, email varchar);""")
cursor.execute("""CREATE TABLE faculty_requests
                    (id integer primary key autoincrement, date datetime, faculty integer);""")
cursor.execute("""CREATE TABLE book_requests
                    (barcode integer primary key, request integer, personal boolean);""")
conn.commit()

cursor.execute("""SELECT SUM(callnumbers.gg_recommended) FROM callnumbers
    INNER JOIN librarians ON librarians.id = callnumbers.assigned_to
    WHERE librarians.name = 'Darren Poley';""")
print (cursor.fetchall())

conn.commit()
conn.close()
