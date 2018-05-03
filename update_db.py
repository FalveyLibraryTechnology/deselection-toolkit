import sqlite3

from src.database_defs import *

conn = sqlite3.connect("database.sqlite")

addNewPostedFiles(conn)
addNewRequests(conn)
updateReviewedCounts(conn)
