import re

with open("output.csv", "w", encoding="utf-8") as output_file:
    output_file.write('Sums')
    with open("lines.txt") as file:
        for i, line in enumerate(file.readlines()):
            matches = re.finditer(r'\d+', line)

            line_sum = sum([int(num_match.group()) for num_match in matches])

            output_file.write(f'\n{line_sum}')
