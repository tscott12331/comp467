import re

# match path after prefix for xytech file paths
xytech_path_re = r'(/hpsans\d{2}/production/)([A-Za-z0-9/\-_]+)'
baselight_prefix = '/baselightfilesystem1/'

# matches the path after baselight file prefix AND the frame numbers into groups
baselight_path_re = rf'((?<={baselight_prefix})[A-Za-z0-9/\-_]+)((\s(\d+))+)'

unique_paths: dict[str, str] = {}

with open('Xytech_spring2026.txt') as xytech_file:
    for xytech_line in xytech_file.readlines():
        path_match = re.search(xytech_path_re, xytech_line)
        if path_match is None:
            continue

        prefix = path_match.group(1)
        suffix = path_match.group(2)
        unique_paths[suffix] = prefix

with open('output.csv', 'w', encoding='utf-8') as output_file:
    # csv column names
    output_file.write("Location,Frames to Fix\n")

    with open('Baselight_export_spring2026.txt') as baselight_file:
        for export_line in baselight_file.readlines():
            path_match = re.search(baselight_path_re, export_line)
            if path_match is None:
                continue
            
            
            path_suffix = path_match.group(1)
            path_prefix = unique_paths.get(path_suffix)
            if path_prefix is None:
                continue
        

            frames = re.split(r'\s+', path_match.group(2).strip())
            xytech_path = f"{path_prefix}{path_suffix}"
            num_frames = len(frames)
            in_range = False
            anchor = frames[0]

            indiv_count = 0
            range_count = 0
            for i, num in enumerate(frames):
                if in_range is False:
                    # start new range
                    anchor = num
                    in_range = True
                    output_file.write(f"{xytech_path},")
                
                if (i == num_frames - 1 or int(frames[i + 1]) - int(num) > 1):
                    # last frame or next frame is too far to add to range
                    # end range
                    in_range = False
                    output_file.write(anchor)
                    if anchor != num:
                        # actually add range text if the current number isnt the anchor
                        output_file.write(f"-{num}")
                        range_count += 1
                    else:
                        indiv_count += 1

                    output_file.write("\n")

            print(f"{xytech_path} Individual: {indiv_count} Ranges: {range_count}")
