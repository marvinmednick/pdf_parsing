#!/usr/bin/env python3

"""
Process PDF to outline blocks and extract text details
"""

import argparse
import pymupdf
import json
import os


def parse_arguments():
    """
    Parse command line arguments
    """
    parser = argparse.ArgumentParser(description='Process PDF to outline blocks and extract text details')
    parser.add_argument('input_file', help='Input PDF file')
    parser.add_argument('-o', '--output_file', help='Output PDF file')
    parser.add_argument('--outline_blocks', action='store_true', help='Outline blocks in the PDF')
    parser.add_argument('-ad', '--appdir', help='Application directory', default='block_extract')
    parser.add_argument('-od', '--output_dir', help='Output directory')
    return parser.parse_args()


def process_pdf(input_file, output_file, outline_blocks, app_dir, output_dir):
    """
    Process PDF to outline blocks and extract text details
    """
    doc = pymupdf.open(input_file)
    pages_data = []

    for page in doc:
        page_data = {
            "page_number": page.number,
            "blocks": []
        }

        blocks = page.get_text("dict", sort=True)["blocks"]
        for block in blocks:
            block_data = {
                "block_number": block["number"],
                "type": block["type"],
                "bbox": block["bbox"],
                "text_segments": []
            }

            if "lines" in block:
                current_font_size = None
                current_font = None
                current_text = ""
                prev_line_num = None

                for line in block["lines"]:
                    for span in line["spans"]:
                        font_size = span["size"]
                        font = span["font"]
                        text = span["text"]
                        line_num = span["origin"][1]

                        if text.strip() == "":
                            current_text += text
                        elif font_size == current_font_size and font == current_font:
                            if prev_line_num is not None and line_num != prev_line_num:
                                current_text += "\n"
                            current_text += text
                        else:
                            if current_text:
                                block_data["text_segments"].append({
                                    "font_size": current_font_size,
                                    "font": current_font,
                                    "text": current_text
                                })
                            current_font_size = font_size
                            current_font = font
                            current_text = text

                        prev_line_num = line_num

                if current_text:
                    block_data["text_segments"].append({
                        "font_size": current_font_size,
                        "font": current_font,
                        "text": current_text
                    })
            else:
                block_data["text_segments"].append({
                    "font_size": None,
                    "font": None,
                    "text": ""
                })

            page_data["blocks"].append(block_data)

            if outline_blocks:
                rect = pymupdf.Rect(block["bbox"])
                page.draw_rect(rect, color=(1, 0, 0), width=2)

        pages_data.append(page_data)

    if outline_blocks:
        doc.save(output_file)

    output_dir_path = os.path.join(app_dir, output_dir)
    os.makedirs(output_dir_path, exist_ok=True)

    json_output_file = os.path.join(output_dir_path, f"{os.path.basename(input_file)[:-4]}_blocks.json")
    with open(json_output_file, 'w', encoding='utf-8') as f:
        json.dump(pages_data, f, ensure_ascii=False, indent=4)


def main():
    """
    Main function
    """
    args = parse_arguments()
    output_dir = args.output_dir if args.output_dir else os.path.basename(args.input_file)[:-4]
    output_file = args.output_file if args.output_file else f"{args.input_file[:-4]}_blocks.pdf"
    process_pdf(args.input_file, output_file, args.outline_blocks, args.appdir, output_dir)


if __name__ == "__main__":
    main()
