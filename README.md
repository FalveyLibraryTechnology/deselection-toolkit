## This project has undergone a major refactoring

This project was migrated to a database system in 2018. Unfortunately, that makes most of these scripts are more customized than may be useful for an open-source project. Just be aware as you look through this code that much of it will have to be adapted to your libraries case.

More information on the database's structure and SQL versions of the reports will be posted soon.

[Updated 2019-02-21]

------

# deselection-toolkit

> Villanova's Collection Review Toolkit

The contents of this repository represent the tools developed for Falvey Memorial Library's deselection process. We are sharing these tools in hope that it will help other libraries with their deselection processes. These tools likely won't work out of the box for you, but will hopefully give your library and any developers a running start to solving the problems of deselection with faculty input.

## Why Falvey Undertook Monograph Reduction

### External factors
 - Evolving library collections and collecting among academic libraries
 - Collaborative collection building among libraries (e.g., HathiTrust, EAST)

### Internal factors
 - Absence of a library-wide systematic collection review
 - Changing need for study/research space
 - The University's status change to a doctoral university in Carnegie Classification

## Our Process

We started in April 2017 by purchasing a GreenGlass report and designing a feedback process with subject librarians.

1. We used the GreenGlass data as **quantitative analysis**. We used the following criteria to get a pool of possible candidates.
    - were purchased prior to 2006;
    - AND have not been circulated for more than 10 years;
    - AND are widely available at other libraries (40+ in the U.S., 4+ in PA)
1. The resulting GreenGlass report was organized by callnumber. Each subject librarian was assigned a number of callnumbers based on topic relevancy. Their task was to take each list of books and remove candidates that didn't meet their own metric of **qualitative analysis**. This reduced the number of books we are deselecting, but allowed librarians familiar with each field to keep high-quality, important, or relevant books in the stacks.
1. The resulting sheets were broken into manageable chunks and made available for faculty to evaluate on a monthly basis described below.
1. The resulting sheets and feedback were analyzed and final reports are generated.

The faculty feedback process at Villanova relies on a multi-step, monthly process.

*At the end of each month*
1. Circulation data is gathered and books that have been checked out since the GreenGlass report are removed from the sheets about to be presented to the faculty. One of our criteria is books must have not circulated in the past 10 years, so we need to disqualify books that have been checked out since April.
1. The website we use to present the data is set up and queued to update in the morning.

*At the start of each month*
1. Capture all of the data from our faculty feedback form, cutting it off at midnight.
1. Update the datbase via Python scripts.
1. Archive the previous months reviewed sheets.
1. Generate final reports for the month and update cumulative reports.
1. Post reports in a location all leadership and staff can access for accessment and book removal.

Faculty feedback is channeled into two categories. The first is books that the faculty member would like to remain in the library's collection. The second are books that faculty members would like to keep for their own personal collections. It's important to note that, in our process, **all faculty feedback is respected**. There are a few rules to make the order of requests fair, but no faculty requests are discarded.

1. We keep any book that a faculty member has submitted for retention, even if it was requested for a personal collection.
1. Books only requested for personal collections are distributed to the faculty member who requested it earliest.

### Lessons Learned

1. To reduce the load on your librarians and your faculty, it is recommended that you identify collections and media types that are exempt from deselection. Remove these items from the Greenglass Reports before your librarians begin their manual review.
1. We have seen that monthly extensions do not cause a significant increase in reserved items but go a long way in soothing faculty anxiety.
1. Most faculty who are upset about the process are best handled by explaining the process in full. At Falvey, faculty reach out to their subject librarians, with whom they already have some rapport, when they have concerns or questions.

## The Reports

These are the reports that we are generating that we find most useful. These files are almost entirely Excel or Excel-compatible files, such as CSVs.

### Each Month

1. All faculty requests, sorted by barcode, including call number, book metadata, faculty name, and whether or not it is a personal request or a retention request.
1. All *effective* faculty requests, grouped by faculty. In this file, books that are requested by multiple parties are resolved following the rules above and are displayed once each.
1. All books requested for personal collections, by call number, with faculty delivery information, for easiest extraction and delivery.
1. A master pull list of all books submitted to faculty that month, minus the ones retained in the collection or in personal collections. All books on this list have been finalized for removal from the collection.
1. Automated email forms. We send each faculty an email containing a list of the books they will be receiving for their personal collection. This form cuts back on manual work significantly for the staff member that coordinates that. This report isn't included in the scripts of this repository, because it is highly customized.

### Cumulative

1. Progress by subject area. Includes numbers and percentages of each collection reviewed and retained by library staff and faculty.
1. Progress broken down by callnumber section.
1. A report of files that were extended beyond their initial month of faculty review with number of items added in those additional months.
1. All faculty requests, as above.
1. All effective faculty requests, as above.
1. All books requested for personal collections, as above.

## The Scripts

Included in this project are the Python scripts developed at Falvey Library to assist in the deselection process. These scripts work around barcode organizing and matching, which we found to be the most reliable data point for uniquely identifying items. So if your input contains anything, make it a barcode. We can get the rest of the data from WorldCat or another source. We have also used ISBN matching for other projects, with good success.

The latest version of the program loads all of the information into an SQLite database which is then queried to generate the reports. This database is described in `db_data/init.sql` and can be setup in any way, although modifying `setup_db.py` may be the easiest.

### `setup_db.py`

Populates all of the data in the database, static and dynamic. Inputs are described below.

### `update_db.py`

Updates the most commonly changed parts of the database:
+ Files posted to faculty (posted_files)
+ Faculty retention requests (faculty_requests)
+ Counts of how many items in the project have been reviewed

### `run_reports_db.py`

Generates all of the above reports. Creates a folder for each month and a Cumulative folder.

## Inputs

For the setup and update scripts, these are the inputs used out of the box. The code to digest these can and should be modified to support your library's needs. All of these files live in the `db_data` folder.

### active_callnumbers.txt

All callnumbers actively in the collection. Saved for progress reports. Only needed in `setup_db.py`.

### gg_callnumbers.txt

All callnumbers recommended by GG for removal, based on our criteria. These will be normalized and saved to `gg_callnumbers_norm.txt` for future database updates, including review counts.

### librarians.json

A JSON file of all of the library staff with the information below. The initials are important in our case because each file posted to faculty has the librarian who generated it in the name.

```js
"FL": {
    "name": "First Last",
    "subject": "Humanities",
    "assignment": ["BX", "PA", "ZA"] // in charge of these call numbers
},
```

### faculty_requests.csv

This is the most important file. It's converted into data in `src/database_defs.py` > `addNewRequests`. Our file is a CSV of form data, with the datetime and raw request body included for parsing. Ours looks like this (simplified):

```txt
Date,Level,Channel,User,Message
"Apr 9, 2018, 10:02:16 AM",INFO,"Sent Emails",Guest,"
There has been a submission of the Collection Directorate Weeding Form.

Faculty First Name:
First

Faculty Last Name:
Last

Faculty Department:
Computer Science

Campus Address:
CSC 555

Barcode:
39346001061763

Title:
A Made-Up CS Book

Destination:
Patron (personal collection)

Comment:
My favorite book - F. Last

Barcode:
39346003186139

Title:
A Made-Up Sequel
...
```

### subject_list.txt

A list of subjects for the program to track, one per line. Books are matched to a subject by which librarian created the faculty report they would be found in.

```txt
Social Sciences
Humanities
STEM
```

### Excluded Files

There is a folder called `excluded` in `db_data` that contains one text file for each collection or list of items automatically excluded from deselection. One of these is the list of books that have been checked out since our GreenGlass report was generated. The first line is the reason for exlusion, the rest of the lines are barcodes, one per line.:

```txt
Checked out since April 1, 2017
39346009142367
39346009142128
39346009140809
...
```
