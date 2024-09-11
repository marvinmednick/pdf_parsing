from tqdm import tqdm
from blocks.block_extractor import process_block_text, check_exclusions
from blocks.image_table_extractor import extract_images_and_tables
from blocks.utils import parse_page_ranges
import re

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


def analyze_pdf(filtered_data, section_parsing_config):
    if section_parsing_config is None:
        section_parsing_config = {}

    default_regex = '(?:Section|Appendix|Annex)\\s+(\\d[\\d\\.]*)\\s+([A-Za-z]+.*)|(\\d[\\d\\.]*)\\s+([A-Za-z]+.*)|([A-Z][\\d\\.]*)\\s+([A-Za-z]+.*)'
    section_regex = re.compile(section_parsing_config.get('section_regex', default_regex))
    section_fields = section_parsing_config.get('section_fields', [
        {'name': 'section_number', 'group': [1, 3, 5]},
        {'name': 'title', 'group': [2, 4, 6]}
    ])

    sections = []
    current_section = None

    for page_data in filtered_data:
        page_number = page_data["page_number"]

        for block in page_data["blocks"]:
            for segment in block["text_segments"]:
                text = segment["text"].strip()

                match = section_regex.match(text)
                if match:
                    if current_section:
                        current_section["end_page"] = page_number - 1
                        sections.append(current_section)

                    current_section = {}
                    for field in section_fields:
                        group = field['group']
                        if isinstance(group, list):
                            for g in group:
                                if match.group(g):
                                    current_section[field['name']] = match.group(g)
                                    break
                        else:
                            current_section[field['name']] = match.group(group)
                    current_section["start_page"] = page_number
                    current_section["end_page"] = None
                    current_section["body_text"] = ""
                elif current_section:
                    current_section["body_text"] += text + "\n"

    if current_section:
        current_section["end_page"] = filtered_data[-1]["page_number"]
        sections.append(current_section)

    return sections
