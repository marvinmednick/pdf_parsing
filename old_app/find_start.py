import argparse
import re
import os

MAX_DOTS = 16
PREFACE_NAME = "<preface>"
TITLE_REGEX = re.compile(r"\d[\d\.]*\s+[A-Za-z]+")


def find_start_lines(input_file):
    with open(input_file, "r") as input:
        lines = input.read().splitlines()
        print("Input")
        lines_for_start = []
        for i, l  in enumerate(lines):
            print(f"Input {i}: {l}")
            lines_for_start.append((i,l))

        output = filter_section_starts(lines_for_start)

        print("\nStarting Lines")
        for i, l in enumerate(output):
            print(f"Start {i:5}: {l}")


# look for starting section
def filter_section_starts(lines):
    starts = [(0, 0, PREFACE_NAME)]
    first_found = False

    for i, line in enumerate(lines):
        # check to see if the line matches the pattern
        if re.match(TITLE_REGEX, line[1]) is not None:
            str_line = line[1].strip()
            # only look at lines without too many dots as these are assumed to
            # be TOC entries
            if line[1].count(".") < MAX_DOTS:
                # after we've found section 1, any section is OK
                if first_found:
                    starts.append((i, line[0], line[1]))

                # First section must start with 1  (and not be 11, 12 etc,
                # but 1.0 or 1.1 is OK)
                elif str_line[0] == "1" and not str_line[1].isdigit():
                    starts.append((i, line[0], line[1]))
                    first_found = True

    outputs = []
    i = 0

    while i < len(starts):
        if (
            starts[i][2] == PREFACE_NAME
            or outputs[-1][2] == PREFACE_NAME
            or is_next(outputs[-1][2], starts[i][2])
        ):

            outputs.append(starts[i])
        else:
            i = find_next(outputs[-1][2], starts, i)

            if i is not None:
                outputs.append(starts[i])
            else:
                i = len(starts)

        i += 1

    return outputs


def extract_parts(section):
    try:
        secnum = section.split(None, 1)[0]
        return [int(p) for p in secnum.split(".") if p]
    except:
        raise ValueError(section)


def is_next(section1, section2):
    parts1 = extract_parts(section1)
    parts2 = extract_parts(section2)

    for i, p1 in enumerate(parts1):
        if i >= len(parts2):
            return False
        elif p1 != parts2[i]:
            if p1 + 1 == parts2[i] and len(parts2) == i + 1:
                return len(parts2)
            else:
                return False

    if len(parts1) == len(parts2) - 1 and parts2[-1] == 1:
        return len(parts2)
    else:
        return False


def find_next(line, starts, index):
    nexts = []

    for i in range(index, len(starts)):
        next_match = is_next(line, starts[i][2])
        if next_match:
            nexts.append([i, next_match, starts[i][2]])

    nexts.sort(key=lambda x: -x[1])

    if len(nexts) > 0:
        return nexts[0][0]
    else:
        return None


def main():
    parser = argparse.ArgumentParser(description='Analyze a PDF file and extract text with bounding boxes.')
    parser.add_argument('pdf_path', help='Path to the PDF file to analyze')
    parser.add_argument('-d', '--dir', default='analyze_pdf_output', help='Application output directory')
    parser.add_argument('-o', '--output', help='Base name for output directory (default: input file base name)')
    
    args = parser.parse_args()

    # Create output directory
    input_base = os.path.splitext(os.path.basename(args.pdf_path))[0]
    output_base = args.output if args.output else input_base
    output_dir = os.path.join(args.dir, output_base)
    os.makedirs(output_dir, exist_ok=True)

    find_start_lines(args.pdf_path)


if __name__ == "__main__":
    main()
