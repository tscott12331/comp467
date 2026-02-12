import re


with open("ingest_this.txt") as file:
    for i, line in enumerate(file.readlines()):
        numFreq: dict[str, int] = {}
        # match numbers
        matches = re.finditer(r'\d+', line)
        for match in matches:
            num = match.group()

            # set frequency to +1 of what was there or just 1
            numFreq[num] = (numFreq.get(num) or 0) + 1

        uniqueNums = len(numFreq)
        if uniqueNums == 0:
            # not gonna print the line info if it didn't have any numbers
            continue

        
        lineStr = f"Line {i + 1} - "
        for j, (num, count) in enumerate(numFreq.items()):
            lineStr += f"{num}, {count} time"
            if count > 1:
                # for plural counts
                lineStr += "s"

            if j != uniqueNums - 1:
                # not last one, append seperator
                # not needed for test case but just in case there were multiple unique numbers in a line
                lineStr += "; "

        print(lineStr)
