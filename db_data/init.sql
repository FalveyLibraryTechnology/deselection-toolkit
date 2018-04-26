-- CLEAR
DROP TABLE IF EXISTS callnumber_sections;
DROP TABLE IF EXISTS excluded_barcodes;
DROP TABLE IF EXISTS excluded_sets;
DROP TABLE IF EXISTS faculty;
DROP TABLE IF EXISTS faculty_book;
DROP TABLE IF EXISTS faculty_request;
DROP TABLE IF EXISTS librarians;
DROP TABLE IF EXISTS posted_books;
DROP TABLE IF EXISTS posted_files;
DROP TABLE IF EXISTS subjects;

-- CREATE STATIC
CREATE TABLE subjects
(
    id    INTEGER PRIMARY KEY AUTOINCREMENT,
    label VARCHAR
);

CREATE TABLE librarians
(
    id       INTEGER PRIMARY KEY AUTOINCREMENT,
    name     VARCHAR,
    initials VARCHAR(3)
);

CREATE TABLE callnumber_sections
(
    section          VARCHAR(3) PRIMARY KEY,
    collection_count INTEGER,
    gg_recommended   INTEGER,
    reviewed_count   INTEGER,
    assigned_to      INTEGER,
    subject          INTEGER
);

CREATE TABLE excluded_sets
(
    id     INTEGER PRIMARY KEY AUTOINCREMENT,
    reason TEXT
);

CREATE TABLE excluded_barcodes
(
    barcode INTEGER,
    set_id  INTEGER
);

CREATE TABLE posted_files
(
    id         INTEGER PRIMARY KEY AUTOINCREMENT,
    name       VARCHAR,
    created_by INTEGER,
    section    VARCHAR(3)
);

CREATE TABLE posted_books
(
    barcode INTEGER PRIMARY KEY AUTOINCREMENT,
    file    INTEGER
);

-- CREATE DYNAMIC
CREATE TABLE faculty
(
    id         INTEGER PRIMARY KEY AUTOINCREMENT,
    name       VARCHAR,
    location   VARCHAR,
    department VARCHAR
);
CREATE TABLE faculty_request
(
    id      INTEGER PRIMARY KEY AUTOINCREMENT,
    date    DATETIME,
    faculty INTEGER
);

CREATE TABLE faculty_book
(
    barcode  INTEGER PRIMARY KEY AUTOINCREMENT,
    request  INTEGER,
    personal BOOLEAN
);
