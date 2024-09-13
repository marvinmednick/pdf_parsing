from tqdm import tqdm
from blocks.block_extractor import process_block_text, check_exclusions
from blocks.image_table_extractor import extract_images_and_tables
from blocks.utils import parse_page_ranges
import pymupdf

def preprocess_pdf(doc, input_file, output_file, outline_blocks, app_dir, output_dir, header_size, footer_size, main_pages, exclude_pages, toc_pages):
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
    toc_data = []

    total_pages = len(doc)
    main_page_numbers = parse_page_ranges(main_pages, total_pages)
    exclude_page_numbers = parse_page_ranges(exclude_pages, total_pages, default_range=[])
    toc_page_numbers = parse_page_ranges(toc_pages, total_pages, default_range=[])

    with tqdm(total=total_pages, desc="Processing Pages", unit="page") as pbar:
        for page_num, page in enumerate(doc, start=1):
            if page_num not in main_page_numbers and page_num not in toc_page_numbers:
                continue

            page_images, page_tables, page_locations, doc_image_index, doc_table_index = extract_images_and_tables(
                doc, page, page_num - 1, output_dir, doc_image_index, doc_table_index
            )

            images.extend(page_images)
            tables.extend(page_tables)
            locations_by_page.append(page_locations)

            page_info = page.get_text("dict")
            blocks = page_info["blocks"]
            header_limit = header_size * page_info['height']
            footer_limit = (1 - footer_size) * page_info['height']
            page_data = {
                "page_number": page.number,
                "blocks": [],
                'filtered_blocks': [],
                'excluded_blocks': [],
                'headers': [],
                'footers': [],
                'height': page_info['height'],
                'width': page_info['width'],
                'header_limit': header_limit,
                'footer_limit': footer_limit,
            }

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

            if page_num not in exclude_page_numbers and not page_num in toc_page_numbers:
                filtered_pages_data.append({
                    "page_number": page.number,
                    "blocks": page_data["filtered_blocks"],
                    'height': page_info['height'],
                    'width': page_info['width'],
                })

            if page_num in toc_page_numbers:
                toc_data.append({
                    "page_number": page.number,
                    "blocks": page_data["filtered_blocks"],
                    'height': page_info['height'],
                    'width': page_info['width'],
                })

            pbar.update(1)

    if outline_blocks:
        doc.save(output_file)

    location_info = {
        'locations_by_page': locations_by_page,
    }

    return pages_data, filtered_pages_data, toc_data, images, tables, location_info


level_start = "1"
allow_dot_zero = True


def is_valid_next_section_number(prev_section, separator, next_section=None):

    # if no previous section, the first section must be one of the f
    # following
    if prev_section is None:
        if next_section in ["1", "1.0", "0", "0.0", "0.1"]:
            return True

        return False

    parts = prev_section.split(".")
    valid_next = []

    prev_section_parts = parts
    prev_section_parts.append(level_start)
    next_valid_section = separator.join(prev_section_parts)
    valid_next.append(next_valid_section)
    # print(f"Checking {next_valid_section}")
    if next_section == next_valid_section:
        print(f"Valid {next_valid_section} {next_section}")
        return True

    while prev_section_parts := prev_section_parts[:-1]:
        prev_section_parts[-1] = str(int(prev_section_parts[-1]) + 1)
        next_valid_section = separator.join(prev_section_parts)
        # print(f"Checking {next_valid_section}")
        if next_section == next_valid_section:
            valid_next.append(next_valid_section)
            print(f"Valid {next_valid_section}")
            return True

        # for the first level, also allow X.0
        if allow_dot_zero and len(prev_section_parts) == 1:
            next_valid_section = next_valid_section + separator + "0"
            valid_next.append(next_valid_section)
            # print(f"Checking {next_valid_section}")
            if next_section == next_valid_section:
                print(f"Valid {next_valid_section}")
                return True

    return False


def analyze_pdf(filtered_data, section_parsing_config, regex_pattern):
    sections = []
    last_section_number = None
    current_section = None

    for page_data in filtered_data:
        page_number = page_data["page_number"]

        for block in page_data["blocks"]:
            for segment in block["text_segments"]:
                text = segment["text"].strip()

                match = regex_pattern.match(text)
                if match:
                    if not is_valid_next_section_number(last_section_number, '.', match.group('number')):
                        print(f"Section number {match.group('number')} isn't valid, continuing with previous section ({last_section_number})")
                        if current_section:
                            current_section["body_text"] += text + "\n"
                        continue

                    last_section_number = match.group('number')
                    # start a new section
                    current_section = {}
                    for group in section_parsing_config['regex_groups']:
                        if isinstance(section_parsing_config[group], dict):
                            current_section[group] = match.group(group)
                        else:
                            current_section[group] = match.group(group)
                    current_section["start_page"] = page_number
                    # since we found the line that has the title, there will not be text yet
                    # so start the section with empty text
                    current_section["body_text"] = ""

                elif current_section:
                    # no new section number, so append this text to the previous section
                    current_section["body_text"] += text + "\n"

                sections.append(current_section)

    return sections
