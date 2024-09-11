from blocks.utils import normalize_bbox

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

    return None, False

def overlaps(bbox1, bbox2):
    return bbox1['x0'] < bbox2['x1'] and bbox1['x1'] > bbox2['x0'] and bbox1['top'] < bbox2['bottom'] and bbox1['bottom'] > bbox2['top']

