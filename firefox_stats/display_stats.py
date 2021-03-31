#!/usr/bin/env python3

# This script can be used to rename a project

import argparse
import datetime
import os
import sqlite3
import sys


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument(
        '--monthly',
        help='Display monthly breakdown',
        action='store_true'
    )
    args = parser.parse_args()

    db_file = os.path.abspath(os.path.join(os.path.dirname(__file__), "db", "stats.db"))
    years = range(2015, datetime.datetime.now().year + 1)

    # Connect to SQLite database
    connection = sqlite3.connect(db_file)
    connection.row_factory = sqlite3.Row
    cursor = connection.cursor()

    month_names = [
        "Jan",
        "Feb",
        "Mar",
        "Apr",
        "May",
        "Jun",
        "Jul",
        "Aug",
        "Sep",
        "Oct",
        "Nov",
        "Dec",
    ]

    for year in years:

        # Get totals per month
        month_totals = {}
        for month in range(1, 13):
            start_date = f"{year}{month:02}01"
            if month == 12:
                end_date = f"{year+1}0101"
            else:
                end_date = f"{year}{month+1:02}01"

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
                FROM stats WHERE day>=? AND day<?",
                (f"{start_date}", f"{end_date}"),
            )
            month_totals[month] = cursor.fetchone()

        # Get totals per year
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
        year_totals = cursor.fetchone()

        # Get last total of the year
        cursor.execute(
            "SELECT * FROM stats WHERE day<=? ORDER BY day DESC",
            (f"{year}1231",),
        )
        final_total = cursor.fetchone()

        print(f"{year}:")
        print(
            f"  Total: {final_total['total']} ({final_total['total_w']}) - Added: {year_totals['added']} ({year_totals['added_w']}) - Removed: {year_totals['removed']} ({year_totals['removed_w']})"
        )
        print("  Added breakdown:")
        browser_perc = round(
            float(year_totals["browser"]) / year_totals["added"] * 100, 2
        )
        devtools_perc = round(
            float(year_totals["devtools"]) / year_totals["added"] * 100, 2
        )
        shared_perc = round(
            float(year_totals["shared"]) / year_totals["added"] * 100, 2
        )
        print(
            f"    Browser: {year_totals['browser']} ({year_totals['browser_w']}) - {browser_perc} %"
        )
        print(
            f"    DevTools: {year_totals['devtools']} ({year_totals['devtools_w']}) - {devtools_perc} %"
        )
        print(
            f"    Shared: {year_totals['shared']} ({year_totals['shared_w']}) - {shared_perc} %"
        )

        if args.monthly:
            print("  Month breakdown (added):")
            for month in range(1, 13):
                if month in month_totals and month_totals[month]["added"] is not None:
                    print(
                        f"    {month_names[month-1]}: {month_totals[month]['added']} ({month_totals[month]['added_w']})"
                    )

    # Clean up and close connection
    connection.close()


if __name__ == "__main__":
    main()
