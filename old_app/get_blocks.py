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


def normalize_bbox(bbox):

    if isinstance(bbox, tuple):
        # Unpack the tuple values
        x0, top, x1, bottom = bbox
        # Create and return the normalized dictionary
        return {'x0': x0, 'top': top, 'x1': x1, 'bottom': bottom}

    elif isinstance(bbox, dict):
        if 'y0' in bbox:
            return {'x0': bbox['x0'], 'top': bbox['y0'], 'x1': bbox['x1'], 'bottom': bbox['y1']}
        else:
            return bbox
    else:
        raise ValueError('Bbox must be a tuple or dictionary.')


def rect_to_dict(rect):
    if isinstance(rect, tuple) and len(rect) == 4:
        return {"x0": rect[0], "top": rect[1], "x1": rect[2], "bottom": rect[3]}
    elif hasattr(rect, 'x0'):
        return {"x0": rect.x0, "top": rect.y0, "x1": rect.x1, "bottom": rect.y1}
    else:
        raise ValueError("Unexpected rect format")

def extract_images_and_tables(doc, page, page_num, output_dir, doc_image_index, doc_table_index):
    print(f"Identifying Images and Tables ... Page {page_num+1}", end="\r")
    images = []
    tables = []
    page_locations = {"images": [], "tables": []}

    # Extract images
    image_list = page.get_images(full=True)
    for img_index, img in enumerate(image_list):
        xref = img[0]
        base_image = doc.extract_image(xref)
        image_bytes = base_image["image"]
        image_filename = f"image_p{page_num+1}_{img_index+1}.png"
        image_path = os.path.join(output_dir, image_filename)
        with open(image_path, "wb") as image_file:
            image_file.write(image_bytes)
        images.append(image_filename)
        doc_image_index += 1
        location_record = {
            "page": page_num,
            "page_index": img_index+1,
            "doc_index": doc_image_index,
            "bbox": rect_to_dict(page.get_image_bbox(img)),
            "file": image_filename
        }
        page_locations["images"].append(location_record)

    # Extract tables
    tables_on_page = page.find_tables()
    for table_index, table in enumerate(tables_on_page):
        table_text = table.extract()
        table_filename = f"table_p{page_num+1}_{table_index+1}.txt"
        table_path = os.path.join(output_dir, table_filename)
        with open(table_path, "w", encoding="utf-8") as table_file:
            table_file.write(str(table_text))
        tables.append(table_filename)
        doc_table_index += 1
        location_record = {
            "page": page_num,
            "page_index": table_index+1,
            "doc_index": doc_table_index,
            "bbox": rect_to_dict(table.bbox),
            "file": table_filename
        }
        page_locations["tables"].append(location_record)

    return images, tables, page_locations, doc_image_index, doc_table_index

def process_block_text(block):
    block_data = {
        "block_number": block["number"],
        "type": block["type"],
        "bbox": normalize_bbox(block["bbox"]),
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

    return block_data


def check_exclusions(block, page_locations, header_limit, footer_limit):
    block_bbox = block["bbox"]
    block_top = block_bbox['top']
    block_bottom = block_bbox['bottom']

    # Check if the block is above the header limit
    if block_top < header_limit:
        return "header", True

    # Check if the block is below the footer limit
    if block_bottom > footer_limit:
        return "footer", True

    # Check if the block overlaps with any image block
    for image_location in page_locations["images"]:
        image_bbox = image_location["bbox"]
        if overlaps(block_bbox, image_bbox):
            return "image", True

    # Check if the block overlaps with any table block
    for table_location in page_locations["tables"]:
        table_bbox = table_location["bbox"]
        if overlaps(block_bbox, table_bbox):
            return "table", True

    # TODO -- not sure if we want this -- this could represent and empty line... need to think more
    # Check for blocks with all empty text segments
    # if all(len(segment['text'].strip()) == 0 for segment in block['text_segments']):
    #    return "empty", True

    return None, False


def overlaps(bbox1, bbox2):
    x1_min, y1_min, x1_max, y1_max = bbox1
    x2_min, y2_min, x2_max, y2_max = bbox2
    return bbox1['x0'] < bbox2['x1'] and bbox1['x1'] > bbox2['x0'] and bbox1['top'] < bbox2['bottom'] and bbox1['bottom'] > bbox2['top']


def process_pdf(doc, input_file, output_file, outline_blocks, app_dir, output_dir, header_size, footer_size):
    """
    Process PDF to outline blocks and extract text details
    """
    images = []
    tables = []
    locations_by_page = []
    doc_image_index = 0
    doc_table_index = 0
    pages_data = []
    filtered_pages_data = []

    for page_num, page in enumerate(doc):
        page_images, page_tables, page_locations, doc_image_index, doc_table_index = extract_images_and_tables(
            doc, page, page_num, output_dir, doc_image_index, doc_table_index
        )
        images.extend(page_images)
        tables.extend(page_tables)
        locations_by_page.append(page_locations)

        page_info = page.get_text("dict")
        blocks = page_info["blocks"]
        page_data = {
            "page_number": page.number,
            "blocks": [],
            'filtered_blocks': [],
            'excluded_blocks': [],
            'headers': [],
            'footers': [],
            'height': page_info['height'],
            'width': page_info['width'],
        }

        header_limit = header_size * page_info['height']
        footer_limit = (1 - footer_size) * page_info['height']

        for block in blocks:
            block_data = process_block_text(block)
            page_data["blocks"].append(block_data)

            exclusion_reason, is_excluded = check_exclusions(block_data, page_locations, header_limit, footer_limit)
            if is_excluded:
                if exclusion_reason == "header":
                    page_data["headers"].append(block_data)
                elif exclusion_reason == "footer":
                    page_data["footers"].append(block_data)
                else:
                    page_data["excluded_blocks"].append(block_data)
            else:
                page_data["filtered_blocks"].append(block_data)

            if outline_blocks:
                rect = pymupdf.Rect(block["bbox"])
                page.draw_rect(rect, color=(1, 0, 0), width=2)

        pages_data.append(page_data)
        filtered_pages_data.append({
            "page_number": page.number,
            "blocks": page_data["filtered_blocks"],
            'height': page_info['height'],
            'width': page_info['width'],
        })

    if outline_blocks:
        doc.save(output_file)

    json_output_file = os.path.join(output_dir, f"{os.path.basename(input_file)[:-4]}_blocks.json")
    with open(json_output_file, 'w', encoding='utf-8') as f:
        json.dump(pages_data, f, ensure_ascii=False, indent=4)

    filtered_json_output_file = os.path.join(output_dir, f"filtered_{os.path.basename(input_file)[:-4]}_blocks.json")
    with open(filtered_json_output_file, 'w', encoding='utf-8') as f:
        json.dump(filtered_pages_data, f, ensure_ascii=False, indent=4)

    with open(os.path.join(output_dir, "images.json"), "w", encoding="utf-8") as f:
        json.dump(images, f, ensure_ascii=False, indent=4)

    with open(os.path.join(output_dir, "tables.json"), "w", encoding="utf-8") as f:
        json.dump(tables, f, ensure_ascii=False, indent=4)

    location_info = {
        'locations_by_page': locations_by_page,
    }
    with open(os.path.join(output_dir, "locations.json"), "w", encoding="utf-8") as f:
        json.dump(location_info, f, ensure_ascii=False, indent=4)

    print(f"Processing Complete{' '*40}")


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
