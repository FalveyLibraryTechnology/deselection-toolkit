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
CREATE TABLE callnumber_sections
(
    cn_section       VARCHAR(3) PRIMARY KEY,
    collection_count INTEGER,
    gg_recommended   INTEGER,
    reviewed_count   INTEGER,
    -- CONNECTIONS
    librarian_id     INTEGER,

    FOREIGN KEY(librarian_id) REFERENCES librarians(librarian_id)
);

CREATE TABLE excluded_sets
(
    set_id INTEGER PRIMARY KEY AUTOINCREMENT,
    reason TEXT
);

CREATE TABLE excluded_barcodes
(
    barcode INTEGER,
    -- CONNECTIONS
    set_id  INTEGER,

    PRIMARY KEY(barcode, set_id),

    FOREIGN KEY(set_id) REFERENCES excluded_sets(set_id)

);

CREATE TABLE librarians
(
    librarian_id INTEGER PRIMARY KEY AUTOINCREMENT,
    name         VARCHAR,
    initials     VARCHAR(3)
);

CREATE TABLE librarian_assignments
(
    cn_section   VARCHAR PRIMARY KEY,
    librarian_id INTEGER,

    FOREIGN KEY(cn_section) REFERENCES callnumber_sections(cn_section),
    FOREIGN KEY(librarian_id) REFERENCES librarians(librarian_id)
);

CREATE TABLE posted_books
(
    barcode         INTEGER PRIMARY KEY,
    callnumber      VARCHAR,
    callnumber_sort VARCHAR,
    cn_section      VARCHAR(3),
    title           VARCHAR,
    author          VARCHAR,
    pub_year        TINYINT,
    -- CONNECTIONS
    file_id         INTEGER,

    FOREIGN KEY(file_id) REFERENCES posted_files(file_id),
    FOREIGN KEY(cn_section) REFERENCES callnumber_sections(cn_section)
);

CREATE TABLE posted_files
(
    file_id INTEGER PRIMARY KEY AUTOINCREMENT,
    name    VARCHAR,
    month   DATE,
    -- CONNECTIONS
    librarian_id INTEGER,

    FOREIGN KEY(librarian_id) REFERENCES librarians(librarian_id)
);

CREATE TABLE sections_subjects
(
    subject_id INTEGER,
    cn_section VARCHAR(3),

    PRIMARY KEY(subject_id, cn_section),

    FOREIGN KEY(subject_id) REFERENCES subjects(subject_id),
    FOREIGN KEY(cn_section) REFERENCES callnumber_sections(cn_section)
);

CREATE TABLE subjects
(
    subject_id INTEGER PRIMARY KEY AUTOINCREMENT,
    label      VARCHAR
);

-- CREATE DYNAMIC
CREATE TABLE faculty
(
    faculty_id INTEGER PRIMARY KEY AUTOINCREMENT,
    name       VARCHAR,
    address    VARCHAR,
    department VARCHAR,
    email      VARCHAR
);
CREATE TABLE faculty_requests
(
    request_id INTEGER PRIMARY KEY AUTOINCREMENT,
    date       DATETIME,
    -- CONNECTIONS
    faculty_id INTEGER,

    FOREIGN KEY(faculty_id) REFERENCES faculty(faculty_id)
);

CREATE TABLE faculty_books
(
    barcode  INTEGER,
    personal BOOLEAN,
    comment  VARCHAR,
    -- CONNECTIONS
    request_id INTEGER,

    PRIMARY KEY(barcode, request_id),

    FOREIGN KEY(request_id) REFERENCES requests(request_id)
);
