#!/usr/bin/env python

"""
PDF to Image Converter

This module provides functionality to convert PDF pages to images using PyMuPDF.
It allows for flexible page selection, output formatting, zoom control, DPI settings,
and various image quality adjustments.
"""

import argparse
import os
import pymupdf


def parse_page_list(page_list):
    """
    Parse a comma-separated string of page numbers and ranges into a sorted list of page numbers.

    Args:
        page_list (str): A string containing page numbers and ranges (e.g., '1,3,7-10,14').

    Returns:
        list: A sorted list of unique page numbers.
    """
    pages = set()
    for item in page_list.split(','):
        if '-' in item:
            start, end = map(int, item.split('-'))
            pages.update(range(start, end + 1))
        else:
            pages.add(int(item))
    return sorted(pages)


def process_pdf(args):
    """
    Process the PDF file according to the provided arguments, converting specified pages to images.

    Args:
        args (argparse.Namespace): Parsed command-line arguments containing processing instructions.

    Returns:
        None
    """
    doc = pymupdf.open(args.input)
    total_pages = doc.page_count

    if args.list:
        pages_to_process = parse_page_list(args.list)
    else:
        start_page = args.start if args.start else 1
        num_pages = args.num if args.num else 1
        pages_to_process = range(start_page, min(start_page + num_pages, total_pages + 1))

    output_base = args.output if args.output else os.path.splitext(args.input)[0]
    zoom = args.zoom
    output_format = args.format.lower()

    for page_num in pages_to_process:
        if page_num > total_pages:
            print(f"Warning: Page {page_num} does not exist in the document. Skipping.")
            continue

        page = doc[page_num - 1]
        mat = pymupdf.Matrix(zoom, zoom)
        pix = page.get_pixmap(matrix=mat)
        
        # Set DPI
        pix.set_dpi(args.dpi_x, args.dpi_y)

        # Apply gamma correction if specified
        if args.gamma != 1.0:
            pix.gamma_with(args.gamma)

        if len(pages_to_process) == 1:
            output_file = f"{output_base}.{output_format}"
        else:
            output_file = f"{output_base}_pg{page_num}.{output_format}"

        # Save with format-specific options
        pix.save(output_file)
        
        print(f"Saved page {page_num} as {output_file}")
        print(f"Image resolution: {pix.xres} x {pix.yres} DPI")

    doc.close()


def main():
    """
    Main function to parse command-line arguments and initiate PDF processing.

    This function sets up the argument parser, processes the command-line arguments,
    and calls the process_pdf function with the parsed arguments.

    Returns:
        None
    """
    parser = argparse.ArgumentParser(description="Convert PDF pages to images.")
    parser.add_argument("input", help="Input PDF file name")
    parser.add_argument("-s", "--start", type=int, help="Start page number (default: 1)")
    parser.add_argument("-n", "--num", type=int, help="Number of pages to process (default: 1)")
    parser.add_argument("-l", "--list", help="Comma-separated list of pages to process (e.g., '1,3,7-10,14')")
    parser.add_argument("-o", "--output", help="Base name for output files")
    parser.add_argument("-f", "--format", choices=["png", "jpg"], default="png", help="Output format (default: png)")
    parser.add_argument("-z", "--zoom", type=float, default=2.5, help="Zoom factor (default: 2.5)")
    parser.add_argument("--dpi-x", type=int, default=300, help="Horizontal DPI (default: 300)")
    parser.add_argument("--dpi-y", type=int, default=300, help="Vertical DPI (default: 300)")
    parser.add_argument("--gamma", type=float, default=1.0, help="Gamma correction factor (default: 1.0)")

    args = parser.parse_args()
    process_pdf(args)


if __name__ == "__main__":
    main()

#!/usr/bin/env python

"""
PDF to Image Converter

This module provides functionality to convert PDF pages to images using PyMuPDF.
It allows for flexible page selection, output formatting, zoom control, DPI settings,
and various image quality adjustments.
"""

import argparse
import os
import pymupdf


def parse_page_list(page_list):
    """
    Parse a comma-separated string of page numbers and ranges into a sorted list of page numbers.

    Args:
        page_list (str): A string containing page numbers and ranges (e.g., '1,3,7-10,14').

    Returns:
        list: A sorted list of unique page numbers.
    """
    pages = set()
    for item in page_list.split(','):
        if '-' in item:
            start, end = map(int, item.split('-'))
            pages.update(range(start, end + 1))
        else:
            pages.add(int(item))
    return sorted(pages)


def process_pdf(args):
    """
    Process the PDF file according to the provided arguments, converting specified pages to images.

    Args:
        args (argparse.Namespace): Parsed command-line arguments containing processing instructions.

    Returns:
        None
    """
    doc = pymupdf.open(args.input)
    total_pages = doc.page_count

    if args.list:
        pages_to_process = parse_page_list(args.list)
    else:
        start_page = args.start if args.start else 1
        num_pages = args.num if args.num else 1
        pages_to_process = range(start_page, min(start_page + num_pages, total_pages + 1))

    output_base = args.output if args.output else os.path.splitext(args.input)[0]
    zoom = args.zoom
    output_format = args.format.lower()

    for page_num in pages_to_process:
        if page_num > total_pages:
            print(f"Warning: Page {page_num} does not exist in the document. Skipping.")
            continue

        page = doc[page_num - 1]
        mat = pymupdf.Matrix(zoom, zoom)
        pix = page.get_pixmap(matrix=mat)
        
        # Set DPI
        pix.set_dpi(args.dpi_x, args.dpi_y)

        # Apply gamma correction if specified
        if args.gamma != 1.0:
            pix.gamma_with(args.gamma)

        if len(pages_to_process) == 1:
            output_file = f"{output_base}.{output_format}"
        else:
            output_file = f"{output_base}_pg{page_num}.{output_format}"

        # Save with format-specific options
        pix.save(output_file)
        
        print(f"Saved page {page_num} as {output_file}")
        print(f"Image resolution: {pix.xres} x {pix.yres} DPI")

    doc.close()


def main():
    """
    Main function to parse command-line arguments and initiate PDF processing.

    This function sets up the argument parser, processes the command-line arguments,
    and calls the process_pdf function with the parsed arguments.

    Returns:
        None
    """
    parser = argparse.ArgumentParser(description="Convert PDF pages to images.")
    parser.add_argument("input", help="Input PDF file name")
    parser.add_argument("-s", "--start", type=int, help="Start page number (default: 1)")
    parser.add_argument("-n", "--num", type=int, help="Number of pages to process (default: 1)")
    parser.add_argument("-l", "--list", help="Comma-separated list of pages to process (e.g., '1,3,7-10,14')")
    parser.add_argument("-o", "--output", help="Base name for output files")
    parser.add_argument("-f", "--format", choices=["png", "jpg"], default="png", help="Output format (default: png)")
    parser.add_argument("-z", "--zoom", type=float, default=2.5, help="Zoom factor (default: 2.5)")
    parser.add_argument("--dpi-x", type=int, default=300, help="Horizontal DPI (default: 300)")
    parser.add_argument("--dpi-y", type=int, default=300, help="Vertical DPI (default: 300)")
    parser.add_argument("--gamma", type=float, default=1.0, help="Gamma correction factor (default: 1.0)")

    args = parser.parse_args()
    process_pdf(args)


if __name__ == "__main__":
    main()
