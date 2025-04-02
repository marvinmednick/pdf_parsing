import json
import argparse
import os
from typing import List, Tuple, Dict, Any

# Constants for table formatting
TABLE_HEADER = "    ┌─────┬────────────┬────────────┐"
TABLE_ROW_FORMAT = "    │ {item:3d} │ {unused:10.2f} │ {used:10.2f} │"
TABLE_FOOTER = "    └─────┴────────────┴────────────┘"


def parse_page_range(page_range: str) -> List[int]:
    """Parse page range string into list of page numbers"""
    if page_range.lower() == "all":
        return ["all"]

    pages = []
    for part in page_range.replace(" ", "").split(","):
        if "-" in part:
            start, end = map(int, part.split("-"))
            pages.extend(range(start, end + 1))
        else:
            pages.append(int(part))
    return pages


def is_text_segment_empty(segment: Dict[str, Any]) -> bool:
    """Check if a text segment is empty or invalid"""
    return (
        "text" not in segment
        or segment.get("text", "").strip() == ""
        or segment.get("font") is None
        or segment.get("font_size") is None
    )


def process_block(block: Dict[str, Any]) -> Tuple[bool, bool]:
    """Analyze block's text segments and return processing flags"""
    text_segments = block.get("text_segments", [])

    if not text_segments:
        return True, False

    empty_segments = [is_text_segment_empty(seg) for seg in text_segments]
    all_empty = all(empty_segments)
    some_empty = any(empty_segments) and not all_empty

    return all_empty, some_empty


def find_margins(
    blocks: List[Dict], width: float, height: float
) -> Tuple[float, float, float, float]:
    """Calculate page margins based on block positions"""
    if not blocks:
        return 0.0, width, 0.0, height

    left = min(block["bbox"]["x0"] for block in blocks)
    right = max(block["bbox"]["x1"] for block in blocks)
    top = min(block["bbox"]["top"] for block in blocks)
    bottom = max(block["bbox"]["bottom"] for block in blocks)

    return left, right, top, bottom


def analyze_vertical_layout(
    blocks: List[Dict], page_height: float
) -> List[Tuple[str, float]]:
    """Analyze vertical layout of used/unused areas"""
    layout = []
    current_y = 0.0

    # Sort blocks by vertical position
    sorted_blocks = sorted(blocks, key=lambda b: b["bbox"]["top"])

    for block in sorted_blocks:
        bbox = block["bbox"]
        if bbox["top"] > current_y:
            # Add unused space before this block
            layout.append(("unused", bbox["top"] - current_y))

        # Add used space for this block
        layout.append(("used", bbox["bottom"] - bbox["top"]))
        current_y = bbox["bottom"]

    # Add final unused space if needed
    if current_y < page_height:
        layout.append(("unused", page_height - current_y))

    return layout


def display_vertical_layout_table(layout: List[Tuple[str, float]]) -> None:
    """Display vertical layout as a formatted table"""
    print("  Vertical layout:")
    print(TABLE_HEADER)
    print("    │ Item│    Unused  │     Used   │")
    print("    ├─────┼────────────┼────────────┤")

    unused = [size for typ, size in layout if typ == "unused"]
    used = [size for typ, size in layout if typ == "used"]

    max_len = max(len(unused), len(used))
    for i in range(max_len):
        u = unused[i] if i < len(unused) else 0.0
        v = used[i] if i < len(used) else 0.0
        print(TABLE_ROW_FORMAT.format(item=i + 1, unused=u, used=v))

    print(TABLE_FOOTER)


def process_and_save_files(
    data: List[Dict], output_dir: str, input_path: str, pages_to_process: List[int]
) -> None:
    """Generate and save sorted/filtered JSON files"""
    os.makedirs(output_dir, exist_ok=True)
    base_name = os.path.splitext(os.path.basename(input_path))[0]

    sorted_data = []
    filtered_data = []

    for page in data:
        page_num = page["page_number"]
        processed_page = page.copy()

        # Sort blocks vertically
        processed_page["blocks"] = sorted(
            page["blocks"], key=lambda b: b["bbox"]["top"]
        )
        sorted_data.append(processed_page)

        # Filter blocks and add partial removal flags
        filtered_page = processed_page.copy()
        filtered_blocks = []

        for block in processed_page["blocks"]:
            ignore, partial = process_block(block)
            if not ignore:
                new_block = block.copy()
                if partial:
                    new_block["partial_removal"] = True
                filtered_blocks.append(new_block)

        filtered_page["blocks"] = filtered_blocks
        filtered_data.append(filtered_page)

    # Save files
    with open(os.path.join(output_dir, f"{base_name}_sorted.json"), "w") as f:
        json.dump(sorted_data, f, indent=2)

    with open(os.path.join(output_dir, f"{base_name}_filtered.json"), "w") as f:
        json.dump(filtered_data, f, indent=2)


def process_page(page: Dict, show_table: bool) -> None:
    """Process and display information for a single page"""
    page_num = page["page_number"]
    width = page["width"]
    height = page["height"]

    print(f"\nPage {page_num}:")
    print(f"  Page size: {width:.2f} x {height:.2f}")

    # Filter blocks
    filtered_blocks = []
    for block in page["blocks"]:
        ignore, partial = process_block(block)
        if not ignore:
            filtered_blocks.append(block)
            if partial:
                print(
                    f"  Block {block.get('block_number', '?')}: Contains partial empty text"
                )

    # Calculate margins
    left, right, top, bottom = find_margins(filtered_blocks, width, height)

    print("\n  Margins:")
    print(f"    Left: 0.00 to {left:.2f}")
    print(f"    Right: {right:.2f} to {width:.2f}")
    print(f"    Top: 0.00 to {top:.2f}")
    print(f"    Bottom: {bottom:.2f} to {height:.2f}")

    print("\n  Used area:")
    print(f"    X: {left:.2f} - {right:.2f}")
    print(f"    Y: {top:.2f} - {bottom:.2f}")

    # Vertical layout analysis
    layout = analyze_vertical_layout(filtered_blocks, height)
    if show_table:
        display_vertical_layout_table(layout)
    else:
        print("\n  Vertical layout:")
        for i, (typ, size) in enumerate(layout, 1):
            print(f"    {i:2d}. {typ.capitalize():6}: {size:.2f}")


def main():
    parser = argparse.ArgumentParser(description="PDF Layout Analyzer")
    parser.add_argument("file_path", help="Input JSON file")
    parser.add_argument(
        "-p", "--pages", default="1", help="Pages to process (e.g., '1-3,5', 'all')"
    )
    parser.add_argument(
        "-o", "--output", default="layout_output", help="Output directory"
    )
    parser.add_argument(
        "-t", "--table", action="store_true", help="Show vertical layout as table"
    )

    args = parser.parse_args()

    # Load and process data
    with open(args.file_path) as f:
        data = json.load(f)

    pages_to_process = parse_page_range(args.pages)
    if pages_to_process == ["all"]:
        pages_to_process = [p["page_number"] for p in data]

    # Process and display pages
    for page in data:
        if page["page_number"] in pages_to_process:
            process_page(page, args.table)

    # Save processed files
    process_and_save_files(data, args.output, args.file_path, pages_to_process)
    print(f"\nOutput files saved to: {args.output}")


if __name__ == "__main__":
    main()
