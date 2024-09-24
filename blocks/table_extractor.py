import os
from blocks.utils import rect_to_dict


def extract_tables(doc, output_dir):
    tables = []
    doc_table_index = 0
    locations = {}

    for page_num, page in enumerate(doc, 1):
        page_tables = []
        # Extract tables
        tables_on_page = page.find_tables()
        for table_index, table in enumerate(tables_on_page, 1):
            table_text = table.extract()
            table_filename = f"new_table_p{page_num}_{table_index}.txt"
            table_path = os.path.join(output_dir, table_filename)
            with open(table_path, "w", encoding="utf-8") as table_file:
                table_file.write(str(table_text))
            tables.append(table_filename)
            location_record = {
                "page": page_num,
                "page_index": table_index,
                "doc_index": doc_table_index,
                "bbox": rect_to_dict(table.bbox),
                "file": table_filename
            }
            doc_table_index += 1
            page_tables.append(location_record)

        locations[page_num] = {'tables': page_tables}

    return tables, locations
