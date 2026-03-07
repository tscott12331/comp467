from argparse import ArgumentParser, Namespace
from datetime import datetime
from typing import Any, Mapping
import pymongo
from pymongo.synchronous.collection import Collection
from pymongo.synchronous.database import Database
from pymongo.typings import _Pipeline
import pandas
import re

def aggregate_search(pipeline: _Pipeline, col1: Collection):
    return col1.aggregate(pipeline)

def get_txt_format_entry(entry):
    return [
        f"Test #: {entry.get('Test #') or "Unknown"}\n",
        f"Build #: {format_build_str(entry.get('Build #') or "Unknown")}\n",
        f"Category: {entry.get('Category') or "Unknown"}\n",
        f"Test Case: {entry.get('Test Case') or "Unknown"}\n",
        f"Expected Result: {entry.get('Expected Result') or "Unknown"}\n",
        f"Actual Result: {entry.get('Actual Result') or "Unknown"}\n",
        f"Repeatable: {entry.get('Repeatable?') or "Unknown"}\n",
        f"Blocker: {entry.get('Blocker?') or "Unknown"}\n",
        f"Test Owner: {entry.get('Test Owner') or "Unknown"}\n\n",
    ]

def search(pipeline: _Pipeline, col1: Collection, out_file_path: str|None, to_csv: bool):
    entries = aggregate_search(pipeline, col1)

    if to_csv:
        dataframe = pandas.DataFrame(entries)
        dataframe = dataframe.drop(columns=['_id'])
        csv = dataframe.to_csv(path_or_buf=out_file_path, index=False)
        if csv is not None:
            print(csv)
    else:
        if out_file_path is None:
            for entry in entries:
                print("".join(get_txt_format_entry(entry)))
        else:
            with open(out_file_path, 'w', encoding='utf-8') as file:
                for entry in entries:
                    file.writelines(get_txt_format_entry(entry))


def format_build_str(build_str) -> str:
    try:
        return datetime.strftime(build_str, "%m/%d/%Y")
    except:
        return  build_str



def entry_to_search_data(entry: dict) -> dict:
    test_case = entry['Test Case'] if 'Test Case' in entry else ""
    expected_result = entry['Expected Result'] if 'Expected Result' in entry else ""
    actual_result = entry['Actual Result'] if 'Actual Result' in entry else ""

    whitespace_re = r'\s+'
    words = re.split(whitespace_re, test_case)
    words.extend(re.split(whitespace_re, expected_result))
    words.extend(re.split(whitespace_re, actual_result))

    if 'Build #' in entry and (isinstance(entry['Build #'], datetime) or len(entry['Build #']) > 0):
        build = format_build_str(entry['Build #'])
    else:
        build = "Unknown"

    return { 'words': set(words), 'build': build }

def load_stopwords(stopwords_file:str|None) -> set[str]:
    if stopwords_file is None:
        return set()
    
    with open(stopwords_file, encoding='utf-8') as file:
        return set(re.split(r'\s+', file.read())[:-1])

def is_over_threshold(bug_words: set[str], entry_words: set[str], threshold: float):
    return len(bug_words.intersection(entry_words)) / len(bug_words) > threshold

def get_common_bugs(entries):
    bugs = []
    for entry in entries:
        if entry['count'] == 1:
            continue

        bug_obj = {
            **entry['original'],
            'Number of Builds': len(entry['builds']),
            'Bugs per Build': "|".join([f'{val} in {key}' for key, val in entry['builds'].items()])
            }

        del bug_obj['_id']
        del bug_obj['Test #']
        del bug_obj['Test Owner']
        del bug_obj['Build #']
        bugs.append(bug_obj)

    return bugs

def thomasscottsearch(pipeline: _Pipeline, col1: Collection, stopwords_file:str|None, out_file_path:str|None, to_csv:bool):
    stopwords = load_stopwords(stopwords_file)

    threshold = .5
    entries = col1.aggregate(pipeline)

    # populate with first test case
    first = entries.next()
    if first is None:
        return []

    first_data = entry_to_search_data(first)
    bugs = [
            {
                'words': first_data['words'].difference(stopwords),
                'builds': {
                    first_data['build']: 1,
                },
                'original': first,
                'count': 1
            }
    ]

    for entry in entries:
        data = entry_to_search_data(entry)
        found_similar = False
        for bug in bugs:
            
            if is_over_threshold(bug['words'], data['words'], threshold):
                bug['builds'][data['build']] = (bug['builds'].get(data['build']) or 0) + 1

                bug['count'] += 1
                found_similar = True
                break

        if not found_similar:
            bugs.append(
                {
                    'words': data['words'].difference(stopwords),
                    'builds': {
                        data['build']: 1,
                    },
                    'original': entry,
                    'count': 1
                }
            )


    bug_objs = get_common_bugs(bugs)
    if to_csv:
        dataframe = pandas.DataFrame(bug_objs)
        csv = dataframe.to_csv(path_or_buf=out_file_path, index=False)
        if csv is not None:
            print(csv)
    else:
        if out_file_path is None:
            for bug in bug_objs:
                print("\n".join([f'{key}: {val}' for key, val in bug.items()]))
                print()
        else:
            with open(out_file_path, 'w', encoding='utf-8') as file:
                for bug in bug_objs:
                    file.writelines([f'{key}: {val}\n' for key, val in bug.items()])
                    file.write("\n")




def get_filter_list(args: Namespace) -> list[Mapping[str, Any]]:
    yes_regex = '^(y|Y)'
    no_regex = '^(n|N)'

    if args.common:
        return [{ 'Repeatable?': { '$regex': no_regex } },
                { 'Blocker?': { '$regex': no_regex } }]

    filter_list = []
    if args.owner is not None:
        filter_list.append({ 'Test Owner': { '$regex': rf'(?i){args.owner}' }})

    if args.repeatable:
        filter_list.append({ 'Repeatable?': { '$regex': yes_regex } })

    if args.blocker:
        filter_list.append({ 'Blocker?': { '$regex': yes_regex } })

    if args.date is not None:
        filter_list.append({ 'Build #': { '$eq': pandas.to_datetime(args.date) } })

    return filter_list

def get_pipeline(filters: list[Mapping[str, Any]], collections: list[Collection]) -> _Pipeline:
    filter: dict[str, Any] = { '$match': {} }
    unions = []
    for i in range(1, len(collections)):
        col = collections[i]
        unions.append({
            '$unionWith': { 'coll': col.name }
            })

    if len(filters) > 0:
        filter['$match']['$and'] = filters
        for union in unions:
            union['$unionWith']['pipeline'] = [filter]


    pipeline = [filter]
    pipeline.extend(unions)

    return pipeline




def config_argparse() -> Namespace:
    parser = ArgumentParser()
    parser.add_argument("-f", "--files", help="input db dump that contains test data", nargs='+')

    parser.add_argument("-o", "--out", help="output file for results")
    parser.add_argument("-C", "--csv", help="format output to csv", action='store_true')

    parser.add_argument("-O", "--owner", help="filter by test owner")
    parser.add_argument("-r", "--repeatable", help="filter by repeatable bugs", action='store_true')
    parser.add_argument("-b", "--blocker", help="filter by blocker bugs", action='store_true')
    parser.add_argument("-d", "--date", help="filter by report date")

    parser.add_argument("-S", "--stopwords_file", help="file containing line seperated stopwords to ignnore in common bug tracking")

    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("-s", "--search", help="search for bugs", action="store_true")
    group.add_argument("-c", "--common", help="retrieve common bugs", action="store_true")

    return parser.parse_args()


def import_dump(dump_file:str, dump_name:str, db: Database) -> Collection:
    data_frame = pandas.read_excel(dump_file)
    data_frame = data_frame.fillna('')
    data = data_frame.to_dict(orient='records')
    col = db[dump_name]
    col.insert_many(data)
    return col
    
def config_mongodb(db_dumps: list[str]) -> list[Collection]:
    myclient = pymongo.MongoClient("mongodb://localhost:27017")
    db = myclient['local']

    cols: list[Collection] = []
    for i, file in enumerate(db_dumps):
        cols.append(import_dump(file, f'dump{i}', db))

    return cols

def cleanup(cols: list[Collection]):
    for col in cols:
        col.drop()


args = config_argparse()

cols = config_mongodb(args.files)

filter_list = get_filter_list(args)

pipeline = get_pipeline(filter_list, cols)

if args.search:
    search(pipeline, cols[0], args.out, args.csv)
elif args.common:
    thomasscottsearch(pipeline, cols[0], args.stopwords_file, args.out, args.csv)
else:
    raise Exception("Expected '--common/-c' or '--search/-c' option")

cleanup(cols)
