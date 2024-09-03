import fitz  # PyMuPDF
import pdfplumber
import json
import argparse
import os
import sys
from reportlab.pdfgen import canvas

count = 0


def format_bbox(rect):
    return f"{{ x0: {rect['x0']:.4}, top: {rect['top']:.4}, x1: {rect['x1']:.4}, bottom: {rect['bottom']:.4} }}"


def rect_to_dict(rect):
    global count

    if isinstance(rect, tuple) and len(rect) == 4:
        return {"x0": rect[0], "top": rect[1], "x1": rect[2], "bottom": rect[3]}
    elif hasattr(rect, 'x0'):
        return {"x0": rect.x0, "top": rect.y0, "x1": rect.x1, "bottom": rect.y1}
    else:
        raise ValueError("Unexpected rect format")


def extract_images_and_tables(pdf_path, output_dir):
    doc = fitz.open(pdf_path)
    images = []
    tables = []
    locations = {"images": [], "tables": []}
    locations_by_page = []
    doc_image_index = 0
    doc_table_index = 0

    for page_num, page in enumerate(doc):
        print(f"Identifying Images and Tables ...  Page {page_num}", end="\r")
        # Extract images
        page_locations = {"images": [], "tables": []}
        locations_by_page.append(page_locations)

        image_list = page.get_images(full=True)
        for img_index, img in enumerate(image_list):
            xref = img[0]
            base_image = doc.extract_image(xref)
            image_bytes = base_image["image"]
            image_filename = f"image_p{page_num+1}_{img_index+1}.png"
            image_path = os.path.join(output_dir, image_filename)
            with open(image_path, "wb") as image_file:
                image_file.write(image_bytes)
            images.append(image_path)
            # print("Image bbox:", page.get_image_bbox(img))
            doc_image_index += 1
            location_record = {
                "page": page_num,
                "page_index": img_index+1,
                "doc_index": doc_image_index,
                "bbox": rect_to_dict(page.get_image_bbox(img)),
                "file": image_filename
            }
            # print("Location Record:", location_record)
            locations["images"].append(location_record)
            page_locations["images"].append(location_record)

        # Extract tables
        tables_on_page = page.find_tables()
        for table_index, table in enumerate(tables_on_page):
            table_text = table.extract()
            table_filename = f"table_p{page_num+1}_{table_index+1}.txt"
            table_path = os.path.join(output_dir, table_filename)
            with open(table_path, "w", encoding="utf-8") as table_file:
                table_file.write(str(table_text))
            tables.append(table_path)
            doc_table_index += 1
            location_record = {
                "page": page_num,
                "page_index": table_index+1,
                "doc_index": doc_table_index,
                "bbox": rect_to_dict(table.bbox),
                "file": table_filename
            }
            locations["tables"].append(location_record)
            page_locations["tables"].append(location_record)
    # Save locations to JSON
        location_info = {
            'locations': locations,
            'locations_by_page': locations_by_page,
        }

    print(f"Identifying Images and Tables Complete{' '*40}")
    return images, tables, location_info


def analyze_pdf(pdf_path, header_size, footer_size, debug_match=False):
    with pdfplumber.open(pdf_path) as pdf:
        pages_output = []
        all_words_output = []

        for page_number, page in enumerate(pdf.pages):
            print(f"Analyzing document ...  Page {page_number}", end="\r")
            page_height = page.height
            page_width = page.width

            # Calculate header and footer bounding boxes
            header_bbox = {
                'x0': 0,
                'top': 0,
                'x1': page_width,
                'bottom': header_size * page_height
            }
            footer_bbox = {
                'x0': 0,
                'top': page_height - (footer_size * page_height),
                'x1': page_width,
                'bottom': page_height
            }

            # Extract lines
            lines = []
            matched_areas = []
            extracted_text = page.extract_text()
            # split the text into lines
            line_texts = extracted_text.split('\n') if extracted_text else []

            for line_num, line in enumerate(line_texts):
                if line.strip():
                    if debug_match:
                        print(f"Line {line_num} -  {line}")
                    search_results = page.search(line, regex=False, y_tolerance=4)
                    bbox_details = None
                    for result in search_results:
                        # Check if the result overlaps with any previously matched areas
                        overlap = False
                        for index, area in enumerate(matched_areas):
                            if (result['x0'] < area['x1'] and result['x1'] > area['x0'] and
                                    result['top'] < area['bottom'] and result['bottom'] > area['top']):
                                overlap = True
                                if debug_match:
                                    print(f"    Overlaps with area {index}:")
                                    print(f"    Area  : {format_bbox(area)}!")
                                    print(f"    Result: {format_bbox(result)}!")
                                break
                        if not overlap:
                            bbox_details = result
                            matched_areas.append(bbox_details)
                            if debug_match:
                                print(f"    Added bbox to matched areas: x0: {format_bbox(result)} -- {len(matched_areas)-1}")
                            break

                    if not bbox_details:
                        if debug_match:
                            print(f"Line not found on page {page_number + 1}: '{line}'")

                        # Attempt to use the bottom of the previous line and the top of the next line
                        if line_num == 0:
                            prev_bottom = 0
                        else:
                            prev_bottom = lines[line_num - 1]['bbox_details']['bottom']

                        if line_num + 1 < len(line_texts) and line_texts[line_num + 1].strip():
                            next_search_results = page.search(line_texts[line_num + 1], regex=False)
                            if next_search_results:
                                next_top = next_search_results[0]['top']
                            else:
                                print(f"ERROR: Search Match not found for line on page {page_number + 1}: '{line}'", file=sys.stderr)
                                print("Skipping")
                                continue
                        else:
                            print(f"ERROR: Search Match not found for line on page {page_number + 1} line {line_num}: '{line}'", file=sys.stderr)
                            print("Skipping")
                            continue

                        bbox_details = {
                            'x0': 0,
                            'top': prev_bottom,
                            'x1': page_width,
                            'bottom': next_top
                        }
                    
                    bbox = {
                        'x0': bbox_details['x0'],
                        'top': bbox_details['top'],
                        'x1': bbox_details['x1'],
                        'bottom': bbox_details['bottom']
                    }
                    
                    lines.append({
                        'id': f'line_{line_num}',
                        'text': line,
                        'bbox_details': bbox_details,
                        'bbox': bbox
                    })

            # Extract words
            words = page.extract_words()

            word_to_line = {}
            unassociated_words = []
            for word in words:
                word_associated = False
                # Find which line this word belongs to
                for line in lines:
                    if (word['top'] >= line['bbox_details']['top'] and 
                        word['bottom'] <= line['bbox_details']['bottom']):
                        word_to_line[word['text']] = line['id']
                        word_associated = True
                        break
                if not word_associated:
                    unassociated_words.append(word)

            # Organize page output
            page_output = {
                'page_number': page_number + 1,
                'header': header_bbox,
                'footer': footer_bbox,
                'lines': {
                    'number_of_lines': len(lines),
                    'lines': []
                }
            }
            
            for line in lines:
                line_info = {
                    'text': line['text'],
                    'bbox_details': line['bbox_details'],
                    'bbox': line['bbox'],
                    'words': []
                }
                for word in words:
                    line_id = word_to_line.get(word['text'])
                    if line_id == line['id']:
                        line_info['words'].append({
                            'text': word['text'],
                            'bbox': {
                                'x0': word['x0'],
                                'top': word['top'],
                                'x1': word['x1'],
                                'bottom': word['bottom']
                            }
                        })
                page_output['lines']['lines'].append(line_info)
            
            # Add unassociated words to the page output
            if unassociated_words:
                page_output['unassociated_words'] = [
                    {
                        'text': word['text'],
                        'bbox': {
                            'x0': word['x0'],
                            'top': word['top'],
                            'x1': word['x1'],
                            'bottom': word['bottom']
                        }
                    } for word in unassociated_words
                ]

            pages_output.append(page_output)

            # Save words if requested
            words_output = {
                'page_number': page_number + 1,
                'words': [
                    {
                        'text': word['text'],
                        'bbox': {
                            'x0': word['x0'],
                            'top': word['top'],
                            'x1': word['x1'],
                            'bottom': word['bottom']
                        }
                    } for word in words
                ]
            }
            all_words_output.append(words_output)

        print(f"Analyzing document complete{' '*60}")
        return pages_output, all_words_output


def filter_text(pages_output, location_info):
    filtered_pages_output = []
    removed_lines_by_page = []
    headers_and_footers_by_page = []

    for page_data in pages_output:
        page_number = page_data['page_number']
        print(f"Filtering ouput ... Page {page_number}", end="\r")
        filtered_lines = []
        used_references = set()
        locations = location_info['locations_by_page'][page_number-1]
        removed_lines = []
        removed_lines_by_page.append(removed_lines)
        header_boundry = page_data['header']['bottom']
        footer_boundry = page_data['footer']['top']
        headers_and_footers = []
        headers_and_footers_by_page.append(headers_and_footers)
        # tolerance is set -- positive indicates that text line
        # can go over the boundry by 'tolerance' and still be 
        # considered within the boundry
        tolerance = 2

        for line_num, line in enumerate(page_data['lines']['lines']):
            # Check if the line overlaps with any image or table
            removed_line = False

            # print(f"{' '*5}Line {line_num} {line['bbox']}")
            for idx, image in enumerate(locations['images']):
                # print(f"{' '*10}Checking image {idx} {image['bbox']}")
                reference = f"[Image {image['doc_index']}: {image['file']}]"
                if not removed_line and image['page'] == page_number - 1 and bboxes_overlap(line['bbox'], image['bbox'], tolerance):
                    # print(f"{' '*15}Found location for Image {reference}")
                    # print(f"{' '*15}Text: {line['text']}")
                    removed_line = {
                        'line_number': line_num,
                        'ref_type': 'image',
                        'reference': reference,
                        'ref_bbox': image['bbox']
                    }
                    removed_lines.append(removed_line)
                    removed_line = True

                # if the top of current line is below the bottom of image
                # we've found next line after the table, and need to insert the reference 
                # before it.
                if reference not in used_references and line_is_below_image(image, line, tolerance):
                    # print(f"Found location for Image {reference}")
                    used_references.add(reference)
                    # Insert reference
                    reference_rec = {
                        'type': 'image',
                        'text': reference,
                        'bbox': image['bbox'],
                    }
                    filtered_lines.append(reference_rec)
                    # print(f"Added Reference {reference_rec}")

            for idx, table in enumerate(locations['tables']):
                # print(f"{' '*10}Checking table {idx} {table['bbox']}")
                reference = f"[Table {table['doc_index']}: {table['file']}]"
                if not removed_line and table['page'] == page_number - 1 and bboxes_overlap(line['bbox'], table['bbox'], tolerance):
                    # print(f"{' '*10}Found overlap with for table {reference}")
                    # print(f"{' '*15}Text: {line['text']}")
                    removed_line = {
                        'line_number': line_num,
                        'ref_type': 'table',
                        'reference': reference,
                        'ref_bbox': table['bbox']
                    }
                    removed_lines.append(removed_line)
                    removed_line = True

                # if the top of current line is below the bottom of table
                # we've found next line after the table, and need to insert the reference 
                # before it.
                if reference not in used_references and line_is_below_table(table, line, tolerance):
                    used_references.add(reference)
                    # Insert reference 
                    reference_rec = {
                        'type': 'table',
                        'text': reference,
                        'bbox': table['bbox'],
                    }
                    filtered_lines.append(reference_rec)
                    # print(f"Added Reference {reference_rec}")

            # check for line being above the header boundry, if
            # so move it to the header and footer list
            if not removed_line and line['bbox']['bottom'] - tolerance < header_boundry:
                header_rec = {
                    'page': page_number,
                    'type': 'header',
                    'text': line['text'],
                    'bbox': line['bbox'],
                }
                headers_and_footers.append(header_rec)
                removed_line = True

            # check for line being below the footer boundry, if
            # so move it to the header and footer list
            if not removed_line and line['bbox']['top'] + tolerance > footer_boundry:
                header_rec = {
                    'page': page_number,
                    'type': 'footer',
                    'text': line['text'],
                    'bbox': line['bbox'],
                }
                headers_and_footers.append(header_rec)
                removed_line = True

            if not removed_line:
                line_rec = {
                    'text': line['text'],
                    'bbox': line['bbox']
                }
                filtered_lines.append(line_rec)

        filtered_page_output = {
            'page_number': page_number,
            'headers_and_footers': headers_and_footers,
            'lines': {
                'number_of_lines': len(filtered_lines),
                'lines': filtered_lines,
            }
        }
        filtered_pages_output.append(filtered_page_output)

    print(f"Filtering complete.{' '*40}")
    return filtered_pages_output


# def is_within_bbox(bbox1, bbox2, tolerance=2):
#     return (bbox1['x0'] < bbox2['x1'] + tolerance and bbox1['x1'] > bbox2['x0'] - tolerance and
#             bbox1['top'] < bbox2['top'] + tolerance and bbox1['bottom'] > bbox2['bottom'] - tolerance)


def bboxes_overlap(rectA, rectB, tolerance=2):
    # Check for overlapping conditions using ands, considering tolerance
    #
    # right of rectA is not to the left of rectB
    # right of rectB is not to the left of rectA
    # bottom of rectA is not above the top of rectB
    # bottom or rectB is not above the top of rectA
    if rectA['x1'] + tolerance >= rectB['x0'] - tolerance and \
       rectB['x1'] + tolerance >= rectA['x0'] - tolerance and \
       rectA['bottom'] + tolerance >= rectB['top'] - tolerance and \
       rectB['bottom'] + tolerance >= rectA['top'] - tolerance:
        return True
    
    return False


def line_is_below_image(image, line, tolerance=2):
    return line['bbox']['top'] + tolerance > image['bbox']['bottom']


def line_is_below_table(table, line, tolerance=2):
    return line['bbox']['top'] + tolerance > table['bbox']['bottom']


# def normalized_bbox(bbox):
#     if 'top' in bbox:
#         return {
#             'x1': bbox['x1'],
#             'x0': bbox['x0'],
#             'top': bbox['y1'],
#             'bottom': bbox['y0'],
#         }
#     else:
#         return bbox
# 

def save_unassociated_words_as_pdf(unassociated_words, page_number, output_dir, page_width, page_height):
    pdf_path = os.path.join(output_dir, f"unassociated_words_page_{page_number + 1}.pdf")
    c = canvas.Canvas(pdf_path, pagesize=(page_width, page_height))
    for word in unassociated_words:
        c.drawString(word['x0'], page_height - word['top'], word['text'])
        c.rect(word['x0'], page_height - word['top'], word['x1'] - word['x0'], word['bottom'] - word['top'], stroke=1, fill=0)
    c.save()


def save_text_lines(pages_output, output_file):
    with open(output_file, 'w', encoding='utf-8') as f:
        for page_data in pages_output:
            for line in page_data['lines']['lines']:
                if line['text'].strip():  # Avoid writing blank lines
                    f.write(line['text'] + '\n')


def main():
    parser = argparse.ArgumentParser(description='Analyze a PDF file and extract text with bounding boxes.')
    parser.add_argument('pdf_path', help='Path to the PDF file to analyze')
    parser.add_argument('-d', '--dir', default='analyze_pdf_output', help='Application output directory')
    parser.add_argument('-o', '--output', help='Base name for output directory (default: input file base name)')
    parser.add_argument('--extract_file', default='extracted_text.json', help='Name of the extracted text JSON file')
    parser.add_argument('--header_size', type=float, default=0.07, help='Header size as a percentage of the page height (e.g., 0.1 for 10%%)')
    parser.add_argument('--footer_size', type=float, default=0.07, help='Footer size as a percentage of the page height (e.g., 0.1 for 10%%)')
    parser.add_argument('--savewords', action='store_true', help='Save all words with bounding boxes to a separate JSON file')
    parser.add_argument('--debug_match', '-dbm', action='store_true', default=False, help='Debug the search to match lines in text to create bbox for line')
    parser.add_argument('--show_missing', action='store_true', help='Generate a PDF showing unassociated words with bounding boxes')
    
    args = parser.parse_args()

    # Create output directory
    input_base = os.path.splitext(os.path.basename(args.pdf_path))[0]
    output_base = args.output if args.output else input_base
    output_dir = os.path.join(args.dir, output_base)
    os.makedirs(output_dir, exist_ok=True)

    # Extract images and tables
    images, tables, location_info = extract_images_and_tables(args.pdf_path, output_dir)

    # Analyze PDF for text
    pages_output, all_words_output = analyze_pdf(args.pdf_path, args.header_size, args.footer_size,args.debug_match)

    # Save extracted text
    extract_path = os.path.join(output_dir, args.extract_file)
    with open(extract_path, 'w') as f:
        json.dump(pages_output, f, indent=2)
    print(f"Extracted text saved to {extract_path}")

    # Save extracted text lines to a text file
    extracted_text_txt_path = os.path.join(output_dir, 'extracted_text.txt')
    save_text_lines(pages_output, extracted_text_txt_path)
    print(f"Extracted text lines saved to {extracted_text_txt_path}")

    # Save words to a separate file if requested
    if args.savewords:
        words_output_path = os.path.join(output_dir, 'words_output.json')
        with open(words_output_path, 'w') as f:
            json.dump(all_words_output, f, indent=2)
        print(f"Words saved to {words_output_path}")

    # Save locations of images and tables
    locations_path = os.path.join(output_dir, 'locations.json')
    with open(locations_path, 'w') as json_file:
        json.dump(location_info, json_file, indent=2)
    print(f"Locations saved to {locations_path}")

    # Filter text based on image and table locations
    filtered_pages_output = filter_text(pages_output, location_info)

    # Save filtered text
    filtered_text_path = os.path.join(output_dir, 'filtered_text.json')
    with open(filtered_text_path, 'w') as f:
        json.dump(filtered_pages_output, f, indent=2)
    print(f"Filtered text saved to {filtered_text_path}")

    # Save headers and footers to JSON file
#    headers_footers_path = os.path.join(output_dir, "headers_and_footers.json")
#    with open(headers_footers_path, 'w', encoding='utf-8') as f:
#        json.dump(headers_and_footers, f, ensure_ascii=False, indent=2)
#
#    print(f"Headers and footers saved to {headers_footers_path}")

    # Save filtered text lines to a text file
    filtered_text_txt_path = os.path.join(output_dir, 'filtered_text.txt')
    save_text_lines(filtered_pages_output, filtered_text_txt_path)
    print(f"Filtered text lines saved to {filtered_text_txt_path}")

    # Show missing words if requested
    if args.show_missing:
        for page_data in pages_output:
            if 'unassociated_words' in page_data:
                save_unassociated_words_as_pdf(
                    page_data['unassociated_words'],
                    page_data['page_number'] - 1,  # Adjusting for zero-based index
                    output_dir,
                    pdfplumber.open(args.pdf_path).pages[page_data['page_number'] - 1].width,
                    pdfplumber.open(args.pdf_path).pages[page_data['page_number'] - 1].height
                )


if __name__ == "__main__":
    main()
