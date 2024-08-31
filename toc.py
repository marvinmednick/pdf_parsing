import re
import sys

def extract_toc(text):
    print("Text being processed:")
    print(text[:500])  # Print first 500 characters
    
    print()
    toc_lists = []

    print("TOC Searching")
    toc_start_list = re.finditer(r'\b(?:Table\s+of\s+Contents|Contents|TOC)\b', text, re.IGNORECASE)
    for i, toc_start in enumerate(toc_start_list):
        print(f"{i} Found TOC Start at {toc_start.start()}")

        print()
    # More flexible TOC detection
    #toc_start = re.search(r'\b(?:Table\s+of\s+Contents|Contents|TOC)\b', text, re.IGNORECASE)
    #if not toc_start:
    #    return None
    
        print(f"TOC found at position: {toc_start.start()}")
    
        # Extract the TOC section
        toc_text = text[toc_start.start():]
        toc_end = re.search(r'\n\n', toc_text)
        if toc_end:
            toc_text = toc_text[:toc_end.start()]
            print(f"Toc end found at {toc_end.start()}")
        else:
            print("No TOC end found")
    
        # More flexible regular expression to match TOC entries
        toc_pattern = r'(?:(?:Chapter|Section|Part)?\.?\s*(\d+(?:\.\d+)*))?\s*(.*?)\s*\.{2,}|…|\s{2,}\s*(\d+)'
        toc_pattern1 = r'(?:(?P<type>Chapter|Section|Part)?\.?\s*(?P<number>\d+(?:\.\d+)*))?\s*(?P<title>.*?)\s*(?:\.{2,}|…|\s{2,})\s*(?P<page>\d+)'

        # print('-'*40, toc_text, '-'*40)

        toc_lines = toc_text.split('\n')
        toc_list = []
        for line in toc_lines:
            print(line)
            if match := re.search(toc_pattern1,line):
                # Print out each named group result
                for name, value in match.groupdict().items():
                    print(f"{name}: {value}")
                original_dict = match.groupdict()
                key_mapping = {
                    'type': 'section_type',
                    'number': 'section_number',
                    'title': 'section_name',
                    'page': 'page_number'
                }
                new_dict = {new_key: original_dict[old_key] for old_key, new_key in key_mapping.items()}
                result_dict = {new_key: (original_dict[old_key] if original_dict[old_key] is not None else 'NA')
                   for old_key, new_key in key_mapping.items()}
                toc_list.append(result_dict)
            else:
                print("No match found.")

    
#         # Find all TOC entries
#         entries = re.findall(toc_pattern, toc_text)
#     
#         print(f"Found {len(entries)} TOC entries:")
#         for entry in entries:
#             print(entry)
#     
#         # Format the results
#         toc_list = []
#         for entry in entries:
#             print(f"Entry {entry}")
#             section_number, section_name, page_number = entry
#             toc_list.append({
#                 'section_number': section_number.strip() if section_number else '<NA>',
#                 'section_name': section_name.strip(),
#                 'page_number': page_number.strip()
#             })
#     
        toc_lists.append(toc_list)

    return toc_lists


with open(sys.argv[1], 'r') as input_file:
    pdf_text = input_file.read()

toc_lists = extract_toc(pdf_text)

if toc_lists:
    for i, toc in enumerate(toc_lists):
        print(f"TOC List {i}")
        for item in toc:
            print(f"Type: {item['section_type']:<10} Section: {item['section_number']:<5} {item['section_name']:<100}, Page: {item['page_number']:>5}")
else:
    print("No Table of Contents found.")
