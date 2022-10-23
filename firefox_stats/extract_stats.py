#!/usr/bin/python3

import argparse
import json
import os
import re
import sqlite3
import sys
from datetime import datetime
from compare_locales import parser
from compare_locales.parser.fluent import FluentEntity, FluentParser
from fluent.syntax import ast as ftl
from fluent.syntax import FluentParser


class StringExtraction:

    excluded_folders = (
        "calendar",
        "chat",
        "editor",
        "extensions",
        "mail",
        "other-licenses",
        "suite",
    )

    def __init__(self, script_path, repository_path, date):
        """Initialize object"""

        # Set defaults
        self.supported_formats = [
            ".dtd",
            ".ftl",
            ".inc",
            ".ini",
            ".properties",
        ]
        self.file_list = []

        self.strings = {}
        self.stats = {}
        # Initialize stats
        for group in ["browser", "devtools", "mobile", "shared", "total"]:
            for sub in ["", "_added", "_removed"]:
                self.stats["{}{}".format(group, sub)] = 0
                self.stats["{}{}_w".format(group, sub)] = 0

        self.script_path = script_path
        self.cache_file = os.path.join(script_path, "cache.json")
        self.repository_path = repository_path.rstrip(os.path.sep)

        if date is None:
            self.date = datetime.utcnow().strftime("%Y%m%d")
        else:
            self.date = date

    def extractFileList(self):
        """Extract the list of supported files"""

        for root, dirs, files in os.walk(self.repository_path, followlinks=True):
            for f in files:
                for supported_format in self.supported_formats:
                    if f.endswith(supported_format):
                        self.file_list.append(os.path.join(root, f))
        self.file_list.sort()

    def getRelativePath(self, file_name):
        """Get the relative path of a filename"""

        relative_path = file_name[len(self.repository_path) + 1 :]

        return relative_path

    def getGroup(self, file_name):
        """Get component based on file name"""

        component = file_name.split(os.path.sep)[0]
        if component in ["browser", "devtools", "mobile"]:
            if component == "browser" and "devtools/" in file_name:
                section = "devtools"
            else:
                section = component
        else:
            section = "shared"

        return section

    def count_words(self, text):
        """Count words in text (from compare-locales)"""
        re_br = re.compile("<br[ \t\r\n]*/?>", re.U)
        re_sgml = re.compile(r"</?\w+.*?>", re.U | re.M)

        text = re_br.sub("\n", text)
        text = re_sgml.sub("", text)
        return len(text.split())

    def diff(self, a, b):
        """Diff two lists"""
        b = set(b)
        return [aa for aa in a if aa not in b]

    def extractStrings(self):
        """Extract strings from all files"""

        self.createCache()
        # If the new cache is identical to the existing one, skip updating the
        # DB and cache file
        if set(self.cache.keys()) == set(self.strings.keys()):
            print("Data has not changed. Skipping...")
        else:
            self.storeTotals()
            self.storeCache()

    def createCache(self):
        """Extract strings in files"""

        # Check if we have a list of strings stored from a previous run
        if os.path.isfile(self.cache_file):
            with open(self.cache_file, "r") as f:
                self.cache = json.load(f)
        else:
            self.cache = {}

        # Create a list of files to analyze
        self.extractFileList()

        for file_path in self.file_list:
            file_extension = os.path.splitext(file_path)[1]
            file_name = self.getRelativePath(file_path)

            # Ignore folders unrelated to Firefox Desktop or Fennec
            if file_name.startswith(self.excluded_folders):
                continue
            if file_name.endswith("region.properties"):
                continue

            file_parser = parser.getParser(file_extension)
            file_parser.readFile(file_path)
            try:
                entities = file_parser.parse()
                for entity in entities:
                    # Ignore Junk
                    if isinstance(entity, parser.Junk):
                        continue

                    string_id = "{}:{}".format(file_name, entity)
                    word_count = entity.count_words()
                    if file_extension == ".ftl":
                        if entity.raw_val != "":
                            self.strings[string_id] = entity.raw_val
                        # Store attributes
                        for attribute in entity.attributes:
                            attr_string_id = "{0}:{1}.{2}".format(
                                file_name, entity, attribute
                            )
                            self.strings[attr_string_id] = attribute.raw_val
                    else:
                        self.strings[string_id] = entity.raw_val

                    # Calculate stats
                    section = self.getGroup(file_name)
                    self.stats[section] += 1
                    self.stats["{}_w".format(section)] += word_count
                    # Add totals, ignoring mobile
                    if section != "mobile":
                        self.stats["total"] += 1
                        self.stats["total_w"] += word_count
            except Exception as e:
                print("Error parsing file: {}".format(file_path))
                print(e)

    def storeCache(self):
        """Store cache file"""
        with open(self.cache_file, "w") as f:
            f.write(json.dumps(self.strings, sort_keys=True))

    def storeTotals(self):
        """Store totals in DB"""

        # Connect to SQLite database
        db_file = os.path.join(self.script_path, "db", "stats.db")
        connection = sqlite3.connect(db_file)
        connection.row_factory = sqlite3.Row
        cursor = connection.cursor()

        def update_stats(str_list, stat_type):
            for string_id in str_list:
                file_name = string_id.split(":")[0]
                section = self.getGroup(file_name)

                # If string is removed, I need to count words from cache
                # instead of the parsed content
                if stat_type == "added":
                    message = self.strings[string_id]
                else:
                    message = self.cache[string_id]

                if file_name.endswith(".ftl"):
                    ftl_parser = FluentParser()
                    ftl_entry = ftl_parser.parse_entry("temp={}".format(message))
                    word_count = FluentEntity(None, ftl_entry).count_words()
                else:
                    word_count = self.count_words(message)
                self.stats["{}_{}".format(section, stat_type)] += 1
                self.stats["{}_{}_w".format(section, stat_type)] += word_count
                if section != "mobile":
                    self.stats["total_{}".format(stat_type)] += 1
                    self.stats["total_{}_w".format(stat_type)] += word_count

        added_strings = self.diff(self.strings.keys(), self.cache.keys())
        update_stats(added_strings, "added")

        removed_strings = self.diff(self.cache.keys(), self.strings.keys())
        update_stats(removed_strings, "removed")

        # Import data
        self.stats["day"] = self.date
        cursor.execute(
            "INSERT INTO stats \
             VALUES (NULL, :day, \
             :browser, :browser_w, :browser_added, :browser_added_w, \
             :browser_removed, :browser_removed_w, \
             :devtools, :devtools_w, :devtools_added, :devtools_added_w, \
             :devtools_removed, :devtools_removed_w, \
             :mobile, :mobile_w, :mobile_added, :mobile_added_w, \
             :mobile_removed, :mobile_removed_w, \
             :shared, :shared_w, :shared_added, :shared_added_w, \
             :shared_removed, :shared_removed_w, \
             :total, :total_w, :total_added, :total_added_w, \
             :total_removed, :total_removed_w)",
            self.stats,
        )

        print("Data stored for {}".format(self.date))
        connection.commit()
        connection.execute("VACUUM")
        connection.close()

    def hasData(self):
        """Check if there's already data for this day"""
        # Connect to SQLite database
        db_file = os.path.join(self.script_path, "db", "stats.db")
        connection = sqlite3.connect(db_file)
        connection.row_factory = sqlite3.Row
        cursor = connection.cursor()

        day = datetime.utcnow().strftime("%Y%m%d")
        # Check if we already have data for this day
        cursor.execute("SELECT ID FROM stats WHERE day=?", (day,))
        data = cursor.fetchone()
        connection.close()

        return False if data is None else True


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("repo_path", help="Path to locale files")
    parser.add_argument("date", help="Date", nargs="?")
    args = parser.parse_args()

    extracted_strings = StringExtraction(
        os.path.abspath(os.path.dirname(__file__)), args.repo_path, args.date
    )
    if extracted_strings.hasData():
        print("Stats are already available for this day")
    else:
        extracted_strings.extractStrings()


if __name__ == "__main__":
    main()
