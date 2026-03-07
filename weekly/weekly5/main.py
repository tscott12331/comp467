from argparse import ArgumentParser

parser = ArgumentParser()
parser.add_argument("-f", "--file", help="path to file you want to count lines", required=True)
parser.add_argument("-v", "--verbose", help="print out each line as it is counted", action="store_true")
ns = parser.parse_args()

with open(ns.file, encoding='utf-8') as file:
    c = 0
    for line in file.readlines():
        c += 1
        if ns.verbose:
            print(line)
    
    print(f"Total lines: {c}")
