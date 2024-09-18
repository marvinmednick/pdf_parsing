from tqdm import tqdm
from blocks.block_extractor import process_block_text, check_exclusions
from blocks.image_table_extractor import extract_images_and_tables
from blocks.utils import parse_page_ranges
from blocks.segments import SegmentAnalyzer
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


def increment_numeric(value):
    return str(int(value) + 1)


numbering_info = {
        'numeric': {
            'initial_section_number': ["1", "1.0", "0", "0.0", "0.1"],
            'level_starts': [0, 1],
            'increment':  increment_numeric,
        },
        'annex_numeric': {
            'initial_section_number': ["A", "A.1", "A.0"],
            'level_starts': [0, 1],
            'increment':  increment_numeric,
        }
}


def is_valid_next_section_number(prev_section, separator, next_section=None, model='numeric'):

    numbering_model = numbering_info[model]
    # if no previous section, the first section must be one of the f
    # following
    if prev_section is None:
        if next_section in numbering_model['initial_section_number']:
            return True

        return False

    parts = prev_section.split(".")

    # check the next section against all of the possible sub-sections
    # based on the list of what digits can a new set of subsections start with
    for next_num in numbering_model['level_starts']:
        # since we're looping through multiple options, 
        # reset our 'prev_section_parts back to parts for each loop/option
        prev_section_parts = parts
        prev_section_parts.append(str(next_num))
        next_valid_section = separator.join(prev_section_parts)

        if next_section == next_valid_section:
            print(f"Valid {next_valid_section} {next_section}")
            return True

    # prev_section_parts will have one (and only one) additional sublevel from above
    # (which will be promptly rempved in the while lop below as
    # the code checks for a possible match at leave sub-level

    while prev_section_parts := prev_section_parts[:-1]:
        prev_section_parts[-1] = numbering_model['increment'](prev_section_parts[-1])
        next_valid_section = separator.join(prev_section_parts)

        if next_section == next_valid_section:
            print(f"Valid {next_valid_section}")
            return True

        # for the first level, also allow X.<level start options>
        if len(prev_section_parts) == 1:
            for next_num in numbering_model['level_starts']:
                next_check = next_valid_section + separator + str(next_num)

                if next_section == next_check:
                    print(f"Valid {next_valid_section}")
                    return True

    return False


def analyze_pdf(filtered_data, analysis_config, section_parsing_config, section_heading_pattern, annex_pattern=None):
    sections = []
    last_section_number = None
    current_section = None

    sa = SegmentAnalyzer(analysis_config)

    for page_data in filtered_data:
        page_number = page_data["page_number"]
        print(f"Analyzing page {page_number}")

        for block in page_data["blocks"]:
            for segment in block["text_segments"]:
                text = segment["text"].strip()

                sa.analyze_segment(text)
                section_match = section_heading_pattern.match(text)
                annex_match = (annex_pattern and annex_pattern.match(text)) or None

                if section_match:
                    if not is_valid_next_section_number(last_section_number, '.', section_match.group('number')):
                        print(f"Section number {section_match.group('number')} isn't valid, continuing with previous section ({last_section_number})")
                        if current_section:
                            current_section["body_text"] += text + "\n"
                        continue

                    last_section_number = section_match.group('number')
                    # start a new section
                    current_section = {
                        "start_page": page_number,
                        "body_text":  ""
                    }
                    # add in all the sections from the regex groups matches
                    for group in section_parsing_config['regex_groups']:
                        if isinstance(section_parsing_config[group], dict):
                            current_section[group] = section_match.group(group)
                        else:
                            current_section[group] = section_match.group(group)
                    # since we found the line that has the title, there will not be text yet
                    # so start the section with empty text
                
                elif annex_match:
                    annex_id = is_annex_start()
                    # start a new section
                    current_section = {
                        "start_page": page_number,
                        "body_text":  "",
                        "annex_id" : annex_id,
                    }
                elif current_section:
                    # no new section number, so append this text to the previous section
                    current_section["body_text"] += text + "\n"

                # else, no current section yet, so no where to put the text, so drop it?
                else:
                    print(f"Text without section: {text}")


                sections.append(current_section)

    return sections
