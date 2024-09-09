#!/usr/bin/env python

import os
import argparse
import pdfplumber
import json
from operator import itemgetter

vertical_spacing_threshold = 3
line_vertical_tolerance = 5
span_vertical_tolerance = 5


class Page:
    def __init__(self, page_number):
        self._lines = []
        self._lines_info = []
        self._line_number = 0
        self._page_number = page_number
        # print(f"Created page {page_number}")

    def add_line(self, line):
        # print(f"Adding line {self._line_number} {len(self._lines)}")
        indent_change = 0

        if self._lines:
            prev_line = self._lines[-1]
            # print("Previous line is ", prev_line.line_number, "Lens", len(self._lines), len(self._lines_info))
            self.add_vertical_spacing(line, prev_line)
            indent_change = line.x0 - prev_line.x0

        line_rec = {
            'page': self._page_number,
            'line_num': self._line_number,
            "type": "line",
            'line_text': line.text,
            'line_chars':  line.line_chars,
            'bbox': line.bbox,
            'indent_change': indent_change
        }
        self._lines.append(line)
        self._lines_info.append(line_rec)
        # print(f"Added line {self._line_number} {line.text}")
        self._line_number += 1

    def add_vertical_spacing(self, line, prev_line):
        line_spacing = line.top - prev_line.bottom
        # print("VLS ",type(line), type(prev_line), line_spacing)

        if line_spacing > vertical_spacing_threshold:
            # print("Adding VLS")
            spacing_rec = {
                "page": self._page_number,
                'line_num': f"line {prev_line.line_number} spacing",
                "type": "v_space",
                "desc": f"vertical spacing: {line_spacing}",
                "vert_space": line_spacing,
                "bottom": line.top,
                "top": prev_line.bottom,
                "x0": min(prev_line.x0, line.x0),
                "x1": max(prev_line.x1, line.x1),
            }
            self._lines_info.append(spacing_rec)
            # print(f"Added Spacing {spacing_rec['line_num']}")

    @property
    def lines(self):
        return self._lines

    @property
    def line_number(self):
        return self._line_number

    @property
    def lines_info(self):
        return self._lines_info


class Line:
    def __init__(self, start_char, line_number):
        self._line_number = line_number
        # print(f"Created line {self._line_number}")
        self._line_chars = [start_char]
        self._x0 = start_char['x0']
        # print("LINIT", type(start_char['x0']), type(self._x0))
        self._x1 = start_char['x1']
        self._top = start_char['top']
        self._bottom = start_char['bottom']
        # print(f"Created line starting as {self._top}")

    def process(self, c, index):
        if not self._on_same_line(c, index):
            return False

        self._add_horiz_space(c, index)
        self._add_char(c, index)
        return True

    def _on_same_line(self, c, index):
        return (c['top'] - self._top) <= line_vertical_tolerance or not self._line_chars

    def _add_char(self, c, index):
        self._line_chars.append(c)
        if (c['bottom'] - self._bottom) >= line_vertical_tolerance and self._bottom != 0:
            print(f"Index {index}: bottom outside of tolerance -  last {c['bottom']} last: {self._bottom} ")
        if not self._x0:
            self._x0 = c['x0']
        elif c['x0'] < self._x0:
            print(f"Index {index}: x0 found before start of line")
            self._x0 = c['x0']

        self._x1 = max(self._x1 or -100, c['x1'])

    def _add_horiz_space(self, c, index):
        # add blank characters if next character x distances is large enough
        # but not on the first segment
        char_width = c['width']
        if self._x1 and (c['x0'] - self._x1) > char_width:
            num_spaces = int((c['x0'] - self._x1) // char_width)
            spacing_rec = {
                "type": "h_space",
                "desc": f"horizontal spacing: {num_spaces} spaces",
                "bottom": c['bottom'],
                "top": c['top'],
                "x0": self._x1,
                "x1": self._x1 + num_spaces*char_width,
                "text": " "*num_spaces,
                "size": c['size'],
                "height": c['height'],
                "fontname": c['fontname'],
            }
            self._line_chars.append(spacing_rec)

    @property
    def line_number(self):
        return self._line_number

    @property
    def text(self):
        return ''.join(lc['text'] for lc in self._line_chars)

    @property
    def bbox(self):
        return {'top': self._top, 'bottom': self._bottom, 'x0': self._x0, 'x1': self._x1}

    @property
    def line_chars(self):
        return self._line_chars

    @property
    def top(self):
        return self._top

    @property
    def bottom(self):
        return self._bottom

    @property
    def x0(self):
        # print("Call X0", type(self._x0), self._x0)
        return self._x0

    @property
    def x1(self):
        return self._x1


def find_lines(chars):

    def add_char_to_line(c, line_chars, cur_start_x, cur_end_x, last_bottom):
        line_chars.append(c)
        if (c['bottom'] - last_bottom) >= line_vertical_tolerance and last_bottom != 0:
            print(f"Index {index}: bottom outside of tolerance -  last {c['bottom']} last: {last_bottom} ")
        if not cur_start_x:
            cur_start_x = c['x0']
        elif c['x0'] < cur_start_x:
            print(f"Index {index}: x0 found before start of line")
            cur_start_x = c['x0']

        cur_end_x = max(cur_end_x or -100, c['x1'])

        return line_chars, cur_start_x, cur_end_x

    # TODO refactor into a class
    lines_by_page = []
    spans_by_page = []
    pages = []
    for pg_num, pg_chars in enumerate(chars, 1):
        page = Page(pg_num)
        pages.append(page)
        prev_line_start_x = 0
        last_top = 0
        last_bottom = 0
        cur_start_x = None
        cur_end_x = None
        line_chars = []
        page_lines = []
        page_lines_obj = []
        line_number = 0
        span_number = 0
        span_chars = []
        cur_line = None
        for index, c in enumerate(pg_chars):
            # check some items
            if round(c['size'], 4) != round(c['height'], 4):
                print(f"Index {index}: Size not equal to height {c}")
            if round(c['bottom'] - c['top'], 4) != round(c['height'], 4):
                print(f"Index {index}: top-bottom not equal to height {c['bottom']} - {c['top']} != {c['height']} {c['bottom'] - c['top']}")
            if c['top'] < last_top:
                print(f"Index {index}: top found out of order")

            # if (c['top'] - last_top) <= span_vertical_tolerance or not span_chars:
            #    continue

            if not cur_line:
                cur_line = Line(c, page.line_number)
            elif not cur_line.process(c, page.line_number):
                page.add_line(cur_line)
                cur_line = Line(c, page.line_number)

            # print(f"Char {index}  lt: {last_top} lb: {last_bottom} top {c['top']} bottom {c['bottom']}")
            # if the top is the same as previous (or if just starting a line) -- add it to the current line
            if (c['top'] - last_top) <= line_vertical_tolerance or not line_chars:

                # add blank characters if next character x distances is large enough
                # but not on the first segment
                char_width = c['width']
                if cur_end_x and (c['x0'] - cur_end_x) > char_width:
                    num_spaces = int((c['x0'] - cur_end_x) // char_width)
                    spacing_rec = {
                        "type": "h_space",
                        "desc": f"horizontal spacing: {num_spaces} spaces",
                        "bottom": c['bottom'],
                        "top": c['top'],
                        "x0": cur_end_x,
                        "x1": cur_end_x + num_spaces*char_width,
                        "text": " "*num_spaces,
                        "size": c['size'],
                        "height": c['height'],
                        "fontname": c['fontname'],
                    }
                    line_chars.append(spacing_rec)

                line_chars, cur_start_x, cur_end_x = add_char_to_line(c, line_chars, cur_start_x, cur_end_x, last_bottom)
#                 line_chars.append(c)
#                 if c['bottom'] != last_bottom and last_bottom != 0:
#                     print("Index {index}: bottom doesn't match last")
#                 if not cur_start_x:
#                     cur_start_x = c['x0']
#                 elif c['x0'] < cur_start_x:
#                     print(f"Index {index}: x0 found before start of line")
#                     cur_start_x = c['x0']
#
#                 cur_end_x = max(cur_end_x, c['x1'])
            else:
                # finished a line and found a new top location
                # print(f"Index {index} new top {c['top']} Last: {last_top}")
                # print(f"**        NEW_TOP:  Char {index}  lt: {last_top} lb: {last_bottom} top: {c['top']} bottom: {c['bottom']}")
                line = {
                    'page': pg_num,
                    'line_num': line_number,
                    "type": "line",
                    'line_text': ''.join(lc['text'] for lc in line_chars),
                    'line_chars':  line_chars,
                    'bbox': {'top': last_top, 'bottom': last_bottom, 'x0': cur_start_x, 'x1': cur_end_x},
                    'indent_change': cur_start_x - prev_line_start_x
                }
                page_lines.append(line)

                line_spacing = c['top'] - last_bottom
                # print(f"VSPACE: {line_spacing} =  {c['top']} - {last_bottom}")

                if line_spacing > vertical_spacing_threshold:
                    # print("Adding VSPACE")
                    spacing_rec = {
                        "page": pg_num,
                        'line_num': f"line {line_number} spacing",
                        "type": "v_space",
                        "desc": f"vertical spacing: {line_spacing}",
                        "vert_space": line_spacing,
                        "bottom": c['top'],
                        "top": last_bottom,
                        "x0": cur_end_x,
                        "x1": cur_end_x + char_width,
                    }
                    page_lines.append(spacing_rec)

                line_number += 1
                prev_line_start_x = cur_start_x
                cur_start_x = None
                cur_end_x = None
                last_top = c['top']
                last_bottom = c['bottom']
                line_chars, cur_start_x, cur_end_x = add_char_to_line(c, [], cur_start_x, cur_end_x, last_bottom)

            last_top = c['top']
            last_bottom = c['bottom']

        # Add the final line
        if cur_line:
            page.add_line(cur_line)
            cur_line = Line(c, page.line_number)
        lines_by_page.append(page_lines)

    return lines_by_page, pages


def extract_chars_from_pdf(file_path, output_directory, top, bottom, x0, x1, store_detail=False):

    with pdfplumber.open(file_path) as pdf:
        char_data = []
        full_char_data = []

        for page in pdf.pages:
            page_height = page.height
            page_width = page.width

            if top is None:
                top = 0
            if bottom is None:
                bottom = page_height
            if x0 is None:
                x0 = 0
            if x1 is None:
                x1 = page_width

            cropped_page = page.crop((x0, top, x1, bottom), strict=False)

            fields_to_keep = ['y0', 'x0', 'y1', 'x1', 'text', 'size', 'height', 'fontname', 'width']
            # fields to rename and adjust to have origin at uppper left instead of bottom left
            fields_to_convert = {'y0': 'bottom', 'y1': 'top'}
            fields_to_copy = [field for field in fields_to_keep if field not in fields_to_convert]

            def convert_origin(height):
                return page_height - height

            # Create a new list with remapped and retained fields
            page_chars = [{**{new_key: convert_origin(d[old_key]) for old_key, new_key in fields_to_convert.items() if old_key in d},
                          **{key: d[key] for key in fields_to_copy if key in d}} for d in cropped_page.chars]

            char_data.append(sorted(page_chars, key=itemgetter('top', 'x0', 'bottom', 'x1')))
            full_char_data.append(sorted(cropped_page.chars, key=itemgetter('top', 'x0', 'bottom', 'x1')))

        base_name = os.path.splitext(os.path.basename(file_path))[0]
        output_file = os.path.join(output_directory, f"{base_name}_chars.json")

        with open(output_file, 'w') as f:
            json.dump(char_data, f, indent=4)

        if store_detail:
            output_file = os.path.join(output_directory, f"{base_name}_detail.json")

            with open(output_file, 'w') as f:
                json.dump(full_char_data, f, indent=4)

        print(f"Words extracted and saved to: {output_file}")
        return char_data


def main():
    parser = argparse.ArgumentParser(description='Extract chars from a PDF document.')
    parser.add_argument('file_path', help='Path to the PDF file.')
    parser.add_argument('-od', '--output_directory', help='Directory to store the output. Default is is the base name of the file.')
    parser.add_argument('-ap', '--app_directory', default='pdf_extract', help='Directory to store the output. Default is "pdf_extract".')
    parser.add_argument('-t', '--top', type=float, help='Top coordinate of the bounding box to extract chars from. Default is top of the page.')
    parser.add_argument('-b', '--bottom', type=float, help='Bottom coordinate of the bounding box to extract chars from. Default is bottom of the page.')
    parser.add_argument('-x0', type=float, help='Left boundary of the bounding box to extract chars from. Default is left edge of the page.')
    parser.add_argument('-x1', type=float, help='Right boundary of the bounding box to extract chars from. Default is right edge of the page.')
    parser.add_argument('-d', '--detail', action='store_true', help='Saves the full detail for all chars')

    args = parser.parse_args()

    if not os.path.exists(args.app_directory):
        os.makedirs(args.app_directory)

    base_name = os.path.splitext(os.path.basename(args.file_path))[0]
    output_directory = args.output_directory or base_name

    output_path = os.path.join(args.app_directory, output_directory)
    if not os.path.exists(output_path):
        os.makedirs(output_path)

    print("Extracting")
    chars = extract_chars_from_pdf(args.file_path, output_path, args.top, args.bottom, args.x0, args.x1, store_detail=args.detail)

    print("Finding Lines")
    lines_data, pages = find_lines(chars)

    output_file = os.path.join(output_path, f"{base_name}_lines.json")
    output_file2 = os.path.join(output_path, f"{base_name}_lines2.json")

    with open(output_file, 'w') as f:
        json.dump(lines_data, f, indent=4)

    # from pprint import pprint
    # print(f"Type: {type(pages[0])} {type(pages[0].lines)}")
    # pprint(pages[0])
    # pprint(pages[0].lines_info)

    pages_data = [pg.lines_info for pg in pages]

    with open(output_file2, 'w') as f:
        json.dump(pages_data, f, indent=4)


if __name__ == '__main__':
    main()
