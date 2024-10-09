import os
from blocks.utils import rect_to_dict
from pymupdf.utils import getColor


def extract_images_and_tables(doc, page, page_num, output_dir, doc_image_index, doc_table_index):
    images = []
    tables = []
    page_locations = {"page": page_num, "images": [], "tables": []}
    # return images, tables, page_locations, doc_image_index, doc_table_index

    # Extract images
    image_list = page.get_images(full=True)
    for img_index, img in enumerate(image_list):
        xref = img[0]
        base_image = doc.extract_image(xref)
        image_bytes = base_image["image"]
        image_filename = f"image_p{page_num}_{img_index+1}.png"
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
        table_filename = f"table_p{page_num}_{table_index+1}.txt"
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
