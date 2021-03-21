#!/usr/bin/env python3

# This script can be used to rename a project

import argparse
import datetime
import os
import sqlite3
import sys


def main():
    db_file = os.path.abspath(os.path.join(os.path.dirname(__file__), "db", "stats.db"))
    years = range(2015, datetime.datetime.now().year + 1)

    # Connect to SQLite database
    connection = sqlite3.connect(db_file)
    connection.row_factory = sqlite3.Row
    cursor = connection.cursor()

    for year in years:
        # Get totals
        cursor.execute(
            "SELECT \
             SUM(total_added) as added, \
             SUM(total_added_w) as added_w, \
             SUM(total_removed) as removed, \
             SUM(total_removed_w) as removed_w \
             FROM stats WHERE day>=? AND day<=?",
            ("{}0101".format(year), "{}1231".format(year)),
        )
        totals = cursor.fetchone()

        # Get last total of the year
        cursor.execute(
            "SELECT * FROM stats WHERE day<=? ORDER BY day DESC",
            ("{}1231".format(year),),
        )
        final_total = cursor.fetchone()

        print(
            "{}: Total: {} ({}) - Added: {} ({}) - Removed: {} ({})".format(
                year,
                final_total["total"],
                final_total["total_w"],
                totals["added"],
                totals["added_w"],
                totals["removed"],
                totals["removed_w"],
            )
        )

    # Clean up and close connection
    connection.close()


if __name__ == "__main__":
    main()
