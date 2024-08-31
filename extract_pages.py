import argparse
import os
import pymupdf

def extract_pages(input_file, output_file, start_page, num_pages):
    # Open the input PDF
    doc = pymupdf.open(input_file)
    
    # Create a new PDF document
    new_doc = pymupdf.open()
    
    # Adjust start_page to 0-based index
    start_page -= 1
    
    # Determine the number of pages to extract
    end_page = min(start_page + num_pages, len(doc))
    pages_to_extract = end_page - start_page
    
    # Copy the specified pages to the new document
    new_doc.insert_pdf(doc, from_page=start_page, to_page=end_page - 1)
    
    # Save the new document
    new_doc.save(output_file)
    print(f"Extracted {pages_to_extract} pages from '{input_file}' to '{output_file}'")
    
    # Close both documents
    doc.close()
    new_doc.close()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Extract pages from a PDF file.")
    parser.add_argument("input_file", help="Input PDF file")
    parser.add_argument("-o", "--output", default="extract_pages.pdf", 
                        help="Output PDF file (default: extract_pages.pdf)")
    parser.add_argument("-s", "--start", type=int, default=1, 
                        help="Start page (default: 1)")
    parser.add_argument("-n", "--num", type=int, default=50, 
                        help="Number of pages to extract (default: 50)")
    
    args = parser.parse_args()
    
    # Ensure the output directory exists
    output_dir = os.path.dirname(args.output)
    if output_dir and not os.path.exists(output_dir):
        os.makedirs(output_dir)
    
    extract_pages(args.input_file, args.output, args.start, args.num)
