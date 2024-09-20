from tqdm import tqdm
from blocks.block_extractor import process_block_text, check_exclusions
from blocks.image_table_extractor import extract_images_and_tables
from blocks.utils import parse_page_ranges, dict_to_rect
from blocks.segments import SegmentAnalyzer
import pymupdf
from pymupdf.utils import getColor  


def preprocess_pdf(files, config):
    """
    Process PDF to outline blocks and extract text details
    """
    images = []
    tables = []
    location_info = []
    doc_image_index = 0
    doc_table_index = 0
    pages_data = []
    filtered_pages_data = []
    toc_data = []

    mu_doc = pymupdf.open(files['input'])
    total_pages = len(mu_doc)
    main_page_numbers = parse_page_ranges(config['include_pages'], total_pages)
    exclude_page_numbers = parse_page_ranges(config['exclude_pages'], total_pages, default_range=[])
    toc_page_numbers = parse_page_ranges(config['toc_pages'], total_pages, default_range=[])

    with tqdm(total=total_pages, desc="Processing Pages", unit="page") as pbar:
        for page_num, page in enumerate(mu_doc, start=1):
            if page_num not in main_page_numbers and page_num not in toc_page_numbers:
                continue

            page_images, page_tables, page_locations, doc_image_index, doc_table_index = extract_images_and_tables(
                mu_doc, page, page_num, files['output_dir'], doc_image_index, doc_table_index)

            images.extend(page_images)
            tables.extend(page_tables)
            location_info.append(page_locations)

            if config['outline_images']:
                for img in page_locations['images']:
                    rect = dict_to_rect(img["bbox"])
                    page.draw_rect(rect, color=getColor('orange'), width=2)

            if config['outline_tables']:
                for tbl in page_locations['tables']:
                    rect = dict_to_rect(img["bbox"])
                    page.draw_rect(rect, color=getColor('green'), width=2)

            page_info = page.get_text("dict")
            blocks = page_info["blocks"]
            header_limit = config['header_size'] * page_info['height']
            footer_limit = (1 - config['footer_size']) * page_info['height']
            page_data = {
                "page_number": page_num,
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
                    block_data['exclusion'] = exclusion_reason

                    if exclusion_reason['type'] == "header":
                        page_data["headers"].append(block_data)
                    elif exclusion_reason['type'] == "footer":
                        page_data["footers"].append(block_data)
                    else:
                        page_data["excluded_blocks"].append(block_data)
                else:
                    page_data["filtered_blocks"].append(block_data)

                if config['outline_blocks']:
                    rect = pymupdf.Rect(block["bbox"])
                    page.draw_rect(rect, color=(1, 0, 0), width=2)

            pages_data.append(page_data)

            if page_num not in exclude_page_numbers and page_num not in toc_page_numbers:
                filtered_pages_data.append({
                    "page_number": page_num,
                    "blocks": page_data["filtered_blocks"],
                    'height': page_info['height'],
                    'width': page_info['width'],
                })

            if page_num in toc_page_numbers:
                toc_data.append({
                    "page_number": page_num,
                    "blocks": page_data["filtered_blocks"],
                    'height': page_info['height'],
                    'width': page_info['width'],
                })

            pbar.update(1)

    if config['outline_blocks'] or config['outline_images'] or config['outline_tables']:
        mu_doc.save(files['output'])

    result = {
            'pages_data': pages_data, 
            'filtered_pages_data': filtered_pages_data, 
            'toc_data': toc_data, 
            'images': images, 
            'tables': tables,
            'location_info': location_info
    }
    return result


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


def analyze_pdf(filtered_data, analysis_config, section_text_dir):

    sega = SegmentAnalyzer(analysis_config, section_text_dir)

    for page_data in filtered_data:
        page_number = page_data["page_number"]
        # print(f"Analyzing page {page_number}")

        for block in page_data["blocks"]:
            block_text = "".join(item["text"] for item in block["text_segments"]).strip()
            debug = False
            # if debug := (page_number > 305 and page_number < 310):
            #     print(f"Analyzing {block_text}")

            sega.analyze_segment(block_text, page_number, debug=debug)

    return sega.get_section_list()
