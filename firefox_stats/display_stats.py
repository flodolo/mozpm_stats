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
             SUM(browser_added) as browser, \
             SUM(browser_added_w) as browser_w, \
             SUM(devtools_added) as devtools, \
             SUM(devtools_added_w) as devtools_w, \
             SUM(shared_added) as shared, \
             SUM(shared_added_w) as shared_w, \
             SUM(total_removed) as removed, \
             SUM(total_removed_w) as removed_w \
             FROM stats WHERE day>=? AND day<=?",
            (f"{year}0101", f"{year}1231"),
        )
        totals = cursor.fetchone()

        # Get last total of the year
        cursor.execute(
            "SELECT * FROM stats WHERE day<=? ORDER BY day DESC",
            (f"{year}1231",),
        )
        final_total = cursor.fetchone()

        print(f"{year}:")
        print(
            f"  Total: {final_total['total']} ({final_total['total_w']}) - Added: {totals['added']} ({totals['added_w']}) - Removed: {totals['removed']} ({totals['removed_w']})"
        )
        print("  Added breakdown:")
        browser_perc = round(float(totals["browser"]) / totals["added"] * 100, 2)
        devtools_perc = round(float(totals["devtools"]) / totals["added"] * 100, 2)
        shared_perc = round(float(totals["shared"]) / totals["added"] * 100, 2)
        print(
            f"    Browser: {totals['browser']} ({totals['browser_w']}) - {browser_perc} %"
        )
        print(
            f"    DevTools: {totals['devtools']} ({totals['devtools_w']}) - {devtools_perc} %"
        )
        print(
            f"    Shared: {totals['shared']} ({totals['shared_w']}) - {shared_perc} %"
        )

    # Clean up and close connection
    connection.close()


if __name__ == "__main__":
    main()
