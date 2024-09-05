#!/usr/bin/env python

"""
Process PDF to outline blocks, extract text details, and identify images and tables
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
    parser.add_argument('--header_size', type=float, default=0.07, help='Header size as a percentage of the page height (e.g., 0.1 for 10%%)')
    parser.add_argument('--footer_size', type=float, default=0.07, help='Footer size as a percentage of the page height (e.g., 0.1 for 10%%)')
    return parser.parse_args()

def format_bbox(rect):
    return f"{{ x0: {rect['x0']:.4}, top: {rect['top']:.4}, x1: {rect['x1']:.4}, bottom: {rect['bottom']:.4} }}"

def rect_to_dict(rect):
    if isinstance(rect, tuple) and len(rect) == 4:
        return {"x0": rect[0], "top": rect[1], "x1": rect[2], "bottom": rect[3]}
    elif hasattr(rect, 'x0'):
        return {"x0": rect.x0, "top": rect.y0, "x1": rect.x1, "bottom": rect.y1}
    else:
        raise ValueError("Unexpected rect format")

def save_image(doc, img, page_num, img_index, output_dir):
    xref = img[0]
    base_image = doc.extract_image(xref)
    image_bytes = base_image["image"]
    image_filename = f"image_p{page_num+1}_{img_index+1}.png"
    image_path = os.path.join(output_dir, image_filename)
    with open(image_path, "wb") as image_file:
        image_file.write(image_bytes)
    return image_filename

def save_table(table, page_num, table_index, output_dir):
    table_text = table.extract()
    table_filename = f"table_p{page_num+1}_{table_index+1}.txt"
    table_path = os.path.join(output_dir, table_filename)
    with open(table_path, "w", encoding="utf-8") as table_file:
        table_file.write(str(table_text))
    return table_filename

def create_location_record(page_num, index, bbox, filename):
    return {
        "page": page_num,
        "page_index": index+1,
        "bbox": rect_to_dict(bbox),
        "file": filename
    }

def extract_images_and_tables(doc, output_dir):
    images = []
    tables = []
    locations = {"images": [], "tables": []}
    locations_by_page = []

    for page_num, page in enumerate(doc):
        print(f"Identifying Images and Tables ... Page {page_num+1}", end="\r")
        page_locations = {"images": [], "tables": []}
        locations_by_page.append(page_locations)

        # Extract images
        image_list = page.get_images(full=True)
        for img_index, img in enumerate(image_list):
            image_filename = save_image(doc, img, page_num, img_index, output_dir)
            images.append(image_filename)
            location_record = create_location_record(page_num, img_index, page.get_image_bbox(img), image_filename)
            locations["images"].append(location_record)
            page_locations["images"].append(location_record)

        # Extract tables
        tables_on_page = page.find_tables()
        for table_index, table in enumerate(tables_on_page):
            table_filename = save_table(table, page_num, table_index, output_dir)
            tables.append(table_filename)
            location_record = create_location_record(page_num, table_index, table.bbox, table_filename)
            locations["tables"].append(location_record)
            page_locations["tables"].append(location_record)

    print(f"Identifying Images and Tables Complete{' '*40}")

    location_info = {
        'locations': locations,
        'locations_by_page': locations_by_page,
    }

    return images, tables, location_info

def identify_header_footer_blocks(pages_data, header_size, footer_size):
    header_footer_data = {}

    for page in pages_data:
        page_number = page['page_number']
        header_footer_data[page_number] = {
            'headers': [],
            'footers': []
        }

        page_height = page['height']
        header_limit = header_size * page_height
        footer_limit = (1 - footer_size) * page_height

        for index, block in enumerate(page['blocks']):
            if 'bbox' in block:
                bbox = block['bbox']
                block_top = bbox[1]
                block_bottom = bbox[3]
                # Check if the block is within the header area
                if block_top < header_limit:
                    header_footer_data[page_number]['headers'].append(block)
                # Check if the block is within the footer area
                if block_bottom > footer_limit:
                    header_footer_data[page_number]['footers'].append(block)

    return header_footer_data, header_limit, footer_limit

def save_header_footer_blocks(header_footer_data, output_dir):
    header_footer_json_file = os.path.join(output_dir, 'header_and_footers.json')
    with open(header_footer_json_file, 'w', encoding='utf-8') as f:
        json.dump(header_footer_data, f, ensure_ascii=False, indent=4)

def process_pdf(doc, input_file, output_file, outline_blocks, app_dir, output_dir, header_size, footer_size):
    """
    Process PDF to outline blocks and extract text details
    """
    images, tables, location_info = extract_images_and_tables(doc, output_dir)

    with open(os.path.join(output_dir, "images.json"), "w", encoding="utf-8") as f:
        json.dump(images, f, ensure_ascii=False, indent=4)

    with open(os.path.join(output_dir, "tables.json"), "w", encoding="utf-8") as f:
        json.dump(tables, f, ensure_ascii=False, indent=4)

    with open(os.path.join(output_dir, "locations.json"), "w", encoding="utf-8") as f:
        json.dump(location_info, f, ensure_ascii=False, indent=4)

    pages_data = []

    for page in doc:
        page_info = page.get_text("dict")
        blocks = page_info["blocks"]
        page_data = {
            "page_number": page.number,
            "blocks": [],
            'filtered_blocks': [],
            'height': page_info['height'],
            'width': page_info['width'],
        }

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

    json_output_file = os.path.join(output_dir, f"{os.path.basename(input_file)[:-4]}_blocks.json")
    with open(json_output_file, 'w', encoding='utf-8') as f:
        json.dump(pages_data, f, ensure_ascii=False, indent=4)

    header_footer_data, header_limit, footer_limit = identify_header_footer_blocks(pages_data, header_size, footer_size)
    save_header_footer_blocks(header_footer_data, output_dir)

def main():
    """
    Main function
    """
    args = parse_arguments()
    output_dir = args.output_dir if args.output_dir else os.path.basename(args.input_file)[:-4]
    app_dir = args.appdir
    output_dir_path = os.path.join(app_dir, output_dir)
    os.makedirs(output_dir_path, exist_ok=True)
    output_file = args.output_file if args.output_file else os.path.join(output_dir_path, f"{os.path.basename(args.input_file)[:-4]}_blocks.pdf")
    doc = pymupdf.open(args.input_file)
    process_pdf(doc, args.input_file, output_file, args.outline_blocks, app_dir, output_dir_path, args.header_size, args.footer_size)

if __name__ == "__main__":
    main()
