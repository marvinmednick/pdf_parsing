import argparse
import os
import json
import fitz  # PyMuPDF
import pdfplumber
from operator import itemgetter
import re

def rect_to_dict(rect):
    if isinstance(rect, tuple) and len(rect) == 4:
        return {"x0": rect[0], "y0": rect[1], "x1": rect[2], "y1": rect[3]}
    elif hasattr(rect, 'x0'):
        return {"x0": rect.x0, "y0": rect.y0, "x1": rect.x1, "y1": rect.y1}
    else:
        raise ValueError("Unexpected rect format")

def extract_images_and_tables(pdf_path, output_dir):
    doc = fitz.open(pdf_path)
    images = []
    tables = []
    locations = {"images": [], "tables": []}

    for page_num, page in enumerate(doc):
        # Extract images
        print(f"Image and Tables page {page_num}")
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
            locations["images"].append({
                "page": page_num,
                "bbox": rect_to_dict(page.get_image_bbox(img)),
                "file": image_filename
            })

        # Extract tables
        tables_on_page = page.find_tables()
        for table_index, table in enumerate(tables_on_page):
            table_text = table.extract()
            table_filename = f"table_p{page_num+1}_{table_index+1}.txt"
            table_path = os.path.join(output_dir, table_filename)
            with open(table_path, "w", encoding="utf-8") as table_file:
                table_file.write(str(table_text))
            tables.append(table_path)
            locations["tables"].append({
                "page": page_num,
                "bbox": rect_to_dict(table.bbox),
                "file": table_filename
            })

    # Save locations to JSON
    with open(os.path.join(output_dir, "locations.json"), "w") as json_file:
        json.dump(locations, json_file, indent=2)

    return images, tables, locations

def is_within_bbox(char, bbox, tolerance=2):
    return (bbox['x0'] - tolerance <= char['x0'] <= bbox['x1'] + tolerance and
            bbox['y0'] - tolerance <= char['top'] <= bbox['y1'] + tolerance)

def sort_text_elements(elements):
    return sorted(elements, key=itemgetter('top', 'x0'))

def inches_to_points(inches):
    return inches * 72  # 1 inch = 72 points

def extract_headers_and_footers(pdf_path, header_size, footer_size, size_unit):
    headers_and_footers = []
    
    with pdfplumber.open(pdf_path) as pdf:
        for page_num, page in enumerate(pdf.pages):
            print(f"Headers and footers page {page_num}")
            page_height = page.height
            words = page.extract_words(keep_blank_chars=True, use_text_flow=True)
            
            if size_unit == 'percent':
                header_boundary = page_height * header_size
                footer_boundary = page_height * (1 - footer_size)
            else:  # inches
                header_boundary = inches_to_points(header_size)
                footer_boundary = page_height - inches_to_points(footer_size)
            
            header_words = [word for word in words if word['top'] < header_boundary]
            footer_words = [word for word in words if word['bottom'] > footer_boundary]
            
            if header_words:
                header_text = ' '.join(word['text'] for word in sorted(header_words, key=lambda w: (w['top'], w['x0'])))
                headers_and_footers.append({
                    "page": page_num + 1,
                    "type": "header",
                    "text": header_text
                })
            
            if footer_words:
                footer_text = ' '.join(word['text'] for word in sorted(footer_words, key=lambda w: (w['bottom'], w['x0'])))
                headers_and_footers.append({
                    "page": page_num + 1,
                    "type": "footer",
                    "text": footer_text
                })
    
    return headers_and_footers

def extract_text(pdf_path, output_dir, locations, header_size, footer_size, size_unit):
    def is_header_or_footer(y, page_height):
        if size_unit == 'percent':
            return y > page_height * (1 - footer_size) or y < page_height * header_size
        else:  # inches
            return y > page_height - inches_to_points(footer_size) or y < inches_to_points(header_size)

    def insert_reference(text, reference, position):
        return text[:position] + reference + text[position:]

    with pdfplumber.open(pdf_path) as pdf:
        all_text = ""
        for page_num, page in enumerate(pdf.pages):
            print(f"Extracting Text {page_num}")
            page_height = page.height
            
            # Extract lines
            lines = page.extract_text().split('\n')
            
            # Process each line
            filtered_lines = []
            for line_num, line in enumerate(lines):
                words = page.extract_words(x_tolerance=3, y_tolerance=3)
                line_words = [w for w in words if w['text'] in line]
                
                if not line_words:
                    continue
                
                line_top = min(w['top'] for w in line_words)
                line_bottom = max(w['bottom'] for w in line_words)
                line_left = min(w['x0'] for w in line_words)
                
                # Check if line is in header/footer
                if is_header_or_footer(line_top, page_height):
                    continue
                
                # Check if line overlaps with images or tables
                if any(is_within_bbox({'x0': line_left, 'top': line_top, 'bottom': line_bottom}, img['bbox']) 
                       for img in locations['images'] if img['page'] == page_num):
                    continue
                
                if any(is_within_bbox({'x0': line_left, 'top': line_top, 'bottom': line_bottom}, table['bbox']) 
                       for table in locations['tables'] if table['page'] == page_num):
                    continue
                
                filtered_lines.append(line)
            
            # Join filtered lines
            page_text = '\n'.join(filtered_lines)
            
            # Insert references to images and tables
            for img in locations["images"]:
                if img["page"] == page_num:
                    insert_position = next((i for i, line in enumerate(filtered_lines) 
                                            if min(w['top'] for w in page.extract_words() if w['text'] in line) > img['bbox']['y1']), 
                                           len(filtered_lines))
                    insert_position = sum(len(line) + 1 for line in filtered_lines[:insert_position])
                    reference = f"\n[Image {img['page']+1}: {img['file']}]\n"
                    page_text = insert_reference(page_text, reference, insert_position)
            
            for table in locations["tables"]:
                if table["page"] == page_num:
                    insert_position = next((i for i, line in enumerate(filtered_lines) 
                                            if min(w['top'] for w in page.extract_words() if w['text'] in line) > table['bbox']['y1']), 
                                           len(filtered_lines))
                    insert_position = sum(len(line) + 1 for line in filtered_lines[:insert_position])
                    reference = f"\n[Table {table['page']+1}: {table['file']}]\n"
                    page_text = insert_reference(page_text, reference, insert_position)
            
            # Remove multiple consecutive newlines
            page_text = re.sub(r'\n{3,}', '\n\n', page_text)
            
            all_text += page_text + f"\n\n--- Page {page_num} Page Break ---\n\n"

    # Save extracted text
    with open(os.path.join(output_dir, "extracted_text.txt"), "w", encoding="utf-8") as text_file:
        text_file.write(all_text)


def main():
    parser = argparse.ArgumentParser(description="Extract images, tables, and text from PDF")
    parser.add_argument("filename", help="Input PDF file")
    parser.add_argument("--header-size", type=float, default=0.06, help="Size of header (default: 0.06)")
    parser.add_argument("--footer-size", type=float, default=0.06, help="Size of footer (default: 0.06)")
    parser.add_argument("--size-unit", choices=['percent', 'inches'], default='percent', help="Unit for header and footer size (default: percent)")
    args = parser.parse_args()

    pdf_path = args.filename
    base_name = os.path.splitext(os.path.basename(pdf_path))[0]
    output_dir = os.path.join("comb", base_name)
    os.makedirs(output_dir, exist_ok=True)

    images, tables, locations = extract_images_and_tables(pdf_path, output_dir)
    extract_text(pdf_path, output_dir, locations, args.header_size, args.footer_size, args.size_unit)

    # Extract headers and footers
    headers_and_footers = extract_headers_and_footers(pdf_path, args.header_size, args.footer_size, args.size_unit)

    # Save headers and footers to JSON file
    headers_footers_path = os.path.join(output_dir, "headers_and_footers.json")
    with open(headers_footers_path, 'w', encoding='utf-8') as f:
        json.dump(headers_and_footers, f, ensure_ascii=False, indent=2)

    print(f"Headers and footers saved to {headers_footers_path}")

if __name__ == "__main__":
    main()
