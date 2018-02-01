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
 - The University’s status change to a doctoral university in Carnegie Classification

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
1. Circulation data is gathered and books that have been checked out since the GreenGlass report are removed from the sheets about to be presented to the faculty. One of our criteria is books must have not circulated in the past 10 years, so we need to disqualify books that have been checked out since April. The script `remove_checked_out.py` assists with this.
1. The website we use to present the data is set up and queued to update in the morning.

*At the start of each month*
1. Capture all of the data from our faculty feedback form, cutting it off at midnight and loading it into a large input file.
1. Run this file through `split_logs.py`, this splits logs into appropriate months for us which takes care of extensions and delays for us.
1. Archive the previous months reviewed sheets.
1. Use `cumulative_reports.py` to generate final reports for the month.

Faculty feedback is channeled into two categories. The first is books that the faculty member would like to remain in the library's collection. The second are books that faculty members would like to keep for their own personal collections. It's important to note that, in our process, **all faculty feedback is respected**. There are a few rules to make the order of requests fair, but no faculty requests are discarded.

## The Scripts

These scripts work around barcode organizing and matching, which we found to be a reliable data point. So if your input contains anything, make it a barcode. We can get the rest of the data from WorldCat or another source. We have also used ISBN matching for other projects, with good success.

### remove_checked_out.py

> Step 1 in our monthly process

This script checks every row for barcodes that are in an up-to-date list of recently checked out barcodes and removes rows that match. The resulting sheets are uploaded for faculty, review.

| Input | Description |
|-------|-------------|
| checkedout_since_greenglass.txt | All of the barcodes that are in the GreenGlass report that have been checked out since the report was generated. |
| Deselection Sheets | Any Excel spreadsheets in the `checked_out/` folder are processed, with disqualified rows removed. |

### split_logs.py

> Step 2 in our monthly process

Our faculty feedback and final reports are very regimented by month. This script takes all of our faculty submissions and splits them by month to match their sources. The following logs are added to the `sources/` folder for the grand finale.

| Input | Description |
|-------|-------------|
| input.csv | Our input at Villanova is one long file that contains the raw form data. There are many ways to go about this, but this was the simplest way for us. |
| Deselection Sheets | Pulled from `sources/` and used to index all of the faculty requests. |
| checkedout_since_greenglass.txt | Used to make sure disqualified barcodes aren't marked as missing. |

Missing or incorrect barcodes are highlighted in the log and incorrect data is checked and repaired by hand. For example, we often get callnumbers instead of barcodes in our form.

This step may be integrated into `cumulative_reports.py` at a future date.

### cumulative_reports.py

> The report generator

This final script is fed by the outputs of the other scripts. There are a few rules to make the faculty requests fair:
1. Requesting books for a personal collection are on a first-come, first-serve basis. Earlier requests override later requests.
1. Requests to keep a book in the collection override requests for personal collections.

| Input | Description |
|-------|-------------|
| Deselection Sheets | These are the Excel sheets presented to the faculty. They contain one book per line with some of the quantitative analysis data. They are all kept in the `sources/` directory. |
| Feedback Logs | The logs are named `{month}-{year}-log.csv` and contain the raw form data form faculty submission, having been cleaned and organized by `split_logs.py`. |

We generate a few reports we find very useful:

| Report | Description |
|--------|-------------|
| master-pull-list.csv | The complete list of books to be removed from the shelves (and donated in our case). It contains all of the individual lists with all of the retention requests (collection and personal) removed. |
| all-retention-by-faculty.csv | A sheet detailing what effect each faculty member had on the deselection in tabbed sections. |
| all-retention-by-callnumber.csv | The same information as the sheet above, but de-sectioned sorted by callnumber for analysis. |
| for-personal-collection-by-faculty.csv | A sheet detailing what books each faculty member will be receiving for their personal collections. |
| for-personal-collection-by-callnumber.csv | The same as above, but de-sectioned and sorted by callnumber, for easier location and processing. |
| personal-retention-emails.csv | A templated email that is generated containing a list of all the books they will be receiving for their collections and a summary of the request override rules. |

| Graph | Description |
|--------|-------------|
| callnumber_areas_by_callnumber.png | A bar for each call number section, showing approximate action by subject. Each bar represents the total number of marked book for that section with sub bars for number of retention requests by faculty and number of personal collection requests. |
| callnumber_areas_by_retention.png | The same as above, but sorted by number retained. |
| callnumber_areas_by_size.png | The same as above, but sorted by number of marked files. |
| faculty.png | Shows a bar for each faculty member showing the number of requested items with a sub bar of how many of those requests are for their personal collection. |

These are generated for each month with an additional cumulative report.
