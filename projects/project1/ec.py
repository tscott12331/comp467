def print_completed_lines(frame_csv_path:str):
    with open(frame_csv_path) as csv:
        content = csv.read()
        lines = content.split('\n')
        for line in lines:
            columns = line.split(',')
            if len(columns) > 2:
                print(line)

print_completed_lines("output-x.csv")
