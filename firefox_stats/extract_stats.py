#!/usr/bin/python

import argparse
from env_setup import import_library
import json
import logging
import os
import re
import subprocess
import sqlite3
import sys
from ConfigParser import SafeConfigParser
from datetime import datetime

logging.basicConfig()

script_path = os.path.abspath(os.path.dirname(__file__))
libraries_path = os.path.join(script_path, 'libraries')

# Import Fluent Python library
import_library(
    libraries_path, 'git', 'python-fluent',
    'https://github.com/projectfluent/python-fluent', '0.4.3')
try:
    from fluent.syntax import ast as ftl
    from fluent.syntax import FluentParser
except ImportError as e:
    print('Error importing python-fluent library')
    print(e)
    sys.exit(1)

# Import compare-locales
import_library(
    libraries_path, 'hg', 'compare-locales',
    'https://hg.mozilla.org/l10n/compare-locales', 'RELEASE_2_1')
try:
    from compare_locales import parser
except ImportError as e:
    print('Error importing compare-locales library')
    print(e)
    sys.exit(1)


class FluentEntity():

    _word_count = None

    def __init__(self, text):
        ftl_parser = FluentParser()
        self.entry = ftl_parser.parse_entry('temp={}'.format(text))

    def count_words(self):
        if self._word_count is None:
            self._word_count = 0

        def count_words(node):
            if isinstance(node, ftl.TextElement):
                self._word_count += len(node.value.split())
            return node

        self.entry.traverse(count_words)

        return self._word_count


class StringExtraction():

    excluded_folders = (
        'calendar',
        'chat',
        'editor',
        'extensions',
        'mail',
        'other-licenses',
        'suite'
    )

    def __init__(self, script_path, repository_path, date):
        '''Initialize object'''

        # Set defaults
        self.supported_formats = [
            '.dtd',
            '.ftl',
            '.inc',
            '.ini',
            '.properties',
        ]
        self.file_list = []

        self.strings = {}
        self.stats = {}
        # Initialize stats
        for group in ['browser', 'devtools', 'mobile', 'shared', 'total']:
            for sub in ['', '_added', '_removed']:
                self.stats['{}{}'.format(group, sub)] = 0
                self.stats['{}{}_w'.format(group, sub)] = 0

        self.script_path = script_path
        self.cache_file = os.path.join(script_path, 'cache.json')
        self.repository_path = repository_path.rstrip(os.path.sep)

        if date is None:
            self.date = datetime.utcnow().strftime('%Y%m%d')
        else:
            self.date = date

    def extractFileList(self):
        '''Extract the list of supported files'''

        for root, dirs, files in os.walk(self.repository_path, followlinks=True):
            for f in files:
                for supported_format in self.supported_formats:
                    if f.endswith(supported_format):
                        self.file_list.append(os.path.join(root, f))
        self.file_list.sort()

    def getRelativePath(self, file_name):
        '''Get the relative path of a filename'''

        relative_path = file_name[len(self.repository_path) + 1:]

        return relative_path

    def getGroup(self, file_name):
        '''Get component based on file name'''

        component = file_name.split(os.path.sep)[0]
        if component in ['browser', 'devtools', 'mobile']:
            if component == 'browser' and 'devtools/' in file_name:
                section = 'devtools'
            else:
                section = component
        else:
            section = 'shared'

        return section

    def count_words(self, text):
        '''Count words in text (from compare-locales)'''
        re_br = re.compile('<br\s*/?>', re.U)
        re_sgml = re.compile('</?\w+.*?>', re.U | re.M)

        text = re_br.sub(u'\n', text)
        text = re_sgml.sub(u'', text)
        return len(text.split())

    def diff(self, a, b):
        '''Diff two lists'''
        b = set(b)
        return [aa for aa in a if aa not in b]

    def extractStrings(self):
        '''Extract strings from all files'''

        self.createCache()
        # If the new cache is identical to the existing one, skip updating the
        # DB and cache file
        if set(self.cache.keys()) == set(self.strings.keys()):
            print('Data has not changed. Skipping...')
        else:
            self.storeTotals()
            self.storeCache()

    def createCache(self):
        '''Extract strings in files'''

        # Check if we have a list of strings stored from a previous run
        if os.path.isfile(self.cache_file):
            self.cache = json.load(open(self.cache_file, 'r'))
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
            if file_name.endswith('region.properties'):
                continue

            file_parser = parser.getParser(file_extension)
            file_parser.readFile(file_path)
            try:
                entities, map = file_parser.parse()
                for entity in entities:
                    # Ignore Junk
                    if isinstance(entity, parser.Junk):
                        continue

                    string_id = u'{}:{}'.format(file_name, unicode(entity))
                    word_count = entity.count_words()
                    if file_extension == '.ftl':
                        if entity.raw_val != '':
                            self.strings[string_id] = entity.raw_val
                        # Store attributes
                        for attribute in entity.attributes:
                            attr_string_id = u'{0}:{1}.{2}'.format(
                                file_name, unicode(entity), unicode(attribute))
                            self.strings[attr_string_id] = attribute.raw_val
                    else:
                        self.strings[string_id] = entity.raw_val

                    # Calculate stats
                    section = self.getGroup(file_name)
                    self.stats[section] += 1
                    self.stats['{}_w'.format(section)] += word_count
                    # Add totals, ignoring mobile
                    if section != 'mobile':
                        self.stats['total'] += 1
                        self.stats['total_w'] += word_count
            except Exception as e:
                print('Error parsing file: {}'.format(file_path))
                print(e)

    def storeCache(self):
        '''Store cache file'''
        f = open(self.cache_file, 'w')
        f.write(json.dumps(self.strings, sort_keys=True))
        f.close()

    def storeTotals(self):
        '''Store totals in DB'''

        # Connect to SQLite database
        db_file = os.path.join(self.script_path, 'db', 'stats.db')
        connection = sqlite3.connect(db_file)
        connection.row_factory = sqlite3.Row
        cursor = connection.cursor()

        # If there is cache, I need to count added/removed strings and words
        if self.cache:

            def update_stats(str_list, stat_type):
                for string_id in str_list:
                    file_name = string_id.split(':')[0]
                    section = self.getGroup(file_name)
                    if file_name.endswith('.ftl'):
                        ftl_entry = FluentEntity(self.strings[string_id])
                        word_count = ftl_entry.count_words()
                    else:
                        word_count = self.count_words(self.strings[string_id])
                    self.stats['{}_{}'.format(section, stat_type)] += 1
                    self.stats['{}_{}_w'.format(
                        section, stat_type)] += word_count
                    if section != 'mobile':
                        self.stats['total_{}'.format(stat_type)] += 1
                        self.stats['total_{}_w'.format(
                            stat_type)] += word_count

            added_strings = self.diff(self.strings.keys(), self.cache.keys())
            update_stats(added_strings, 'added')

            removed_strings = self.diff(self.cache.keys(), self.strings.keys())
            update_stats(removed_strings, 'removed')

        # Import data
        self.stats['day'] = self.date
        cursor.execute(
            'INSERT INTO stats \
             VALUES (NULL, :day, \
             :browser, :browser_w, :browser_added, :browser_added_w, :browser_removed, :browser_removed_w, \
             :devtools, :devtools_w, :devtools_added, :devtools_added_w, :devtools_removed, :devtools_removed_w, \
             :mobile, :mobile_w, :mobile_added, :mobile_added_w, :mobile_removed, :mobile_removed_w, \
             :shared, :shared_w, :shared_added, :shared_added_w, :shared_removed, :shared_removed_w, \
             :total, :total_w, :total_added, :total_added_w, :total_removed, :total_removed_w)',
            self.stats
        )

        print('Data stored for {}'.format(self.date))
        connection.execute('VACUUM')
        connection.commit()
        connection.close()

    def hasData(self):
        ''' Check if there's already data for this day'''
        # Connect to SQLite database
        db_file = os.path.join(self.script_path, 'db', 'stats.db')
        connection = sqlite3.connect(db_file)
        connection.row_factory = sqlite3.Row
        cursor = connection.cursor()

        day = datetime.utcnow().strftime('%Y%m%d')
        # Check if we already have data for this day
        cursor.execute(
            'SELECT ID FROM stats WHERE day=?',
            (day,)
        )
        data = cursor.fetchone()
        connection.close()

        return False if data is None else True


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('repo_path', help='Path to locale files')
    parser.add_argument('date', help='Date', nargs='?')
    args = parser.parse_args()

    extracted_strings = StringExtraction(
        os.path.abspath(os.path.dirname(__file__)),
        args.repo_path, args.date)
    if extracted_strings.hasData():
        print('Stats are already available for this day')
    else:
        extracted_strings.extractStrings()


if __name__ == '__main__':
    main()
