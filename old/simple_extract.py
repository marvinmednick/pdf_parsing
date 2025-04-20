#!/usr/bin/env python

import pdfplumber
import sys

with pdfplumber.open(sys.argv[1]) as reader:

    pages = reader.pages
    print(f"Document has {len(pages)} Pages")

    for page_num, page in enumerate(pages):
        print(f"Page {page_num}")
        print('='*80)
        page_text = page.extract_text()
        if page_text:
            page_lines = page_text.split('\n')
            for i, line in enumerate(page_lines):
                print(f"{i:3} : {line[0:101]}")
        else:
            print("No Text found")
        print()
