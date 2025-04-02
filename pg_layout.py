import json
import argparse
import os
from typing import List, Tuple, Dict, Any, Set

# Table formatting constants
TABLE_HEADER = "    ┌─────┬────────────┬────────────┬────────────────────────────┐"
TABLE_ROW_FORMAT = "    │ {item:3d} │ {unused:10.2f} │ {used:10.2f} │ {fonts:25} │"
TABLE_FOOTER = "    └─────┴────────────┴────────────┴────────────────────────────┘"


class FontCollector:
    def __init__(self):
        self.page_fonts: Set[str] = set()
        self.combined_fonts: Set[str] = set()

    def add_font(self, segment: Dict[str, Any]):
        if segment.get("font") and segment.get("font_size"):
            font_str = f"{segment['font']} {segment['font_size']}"
            self.page_fonts.add(font_str)
            self.combined_fonts.add(font_str)

    def reset_page(self):
        self.page_fonts = set()


def parse_page_range(page_range: str) -> List[int]:
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
    return (
        not segment.get("text", "").strip()
        or segment.get("font") is None
        or segment.get("font_size") is None
    )


def process_block(
    block: Dict[str, Any], font_collector: FontCollector
) -> Tuple[bool, bool]:
    text_segments = block.get("text_segments", [])
    if not text_segments:
        return True, False

    all_empty = True
    some_empty = False

    for seg in text_segments:
        font_collector.add_font(seg)
        empty = is_text_segment_empty(seg)
        if not empty:
            all_empty = False
        else:
            some_empty = True

    return all_empty, (some_empty and not all_empty)


def find_margins(
    blocks: List[Dict], width: float, height: float
) -> Tuple[float, float, float, float]:
    if not blocks:
        return 0.0, width, 0.0, height

    left = min(b["bbox"]["x0"] for b in blocks)
    right = max(b["bbox"]["x1"] for b in blocks)
    top = min(b["bbox"]["top"] for b in blocks)
    bottom = max(b["bbox"]["bottom"] for b in blocks)
    return left, right, top, bottom


def analyze_vertical_layout(
    blocks: List[Dict], page_height: float
) -> List[Tuple[str, float, Set[str]]]:
    layout = []
    current_y = 0.0
    sorted_blocks = sorted(blocks, key=lambda b: b["bbox"]["top"])

    for block in sorted_blocks:
        bbox = block["bbox"]
        if bbox["top"] > current_y:
            layout.append(("unused", bbox["top"] - current_y, set()))

        block_fonts = set()
        for seg in block.get("text_segments", []):
            if seg.get("font") and seg.get("font_size"):
                block_fonts.add(f"{seg['font']} {seg['font_size']}")

        layout.append(("used", bbox["bottom"] - bbox["top"], block_fonts))
        current_y = bbox["bottom"]

    if current_y < page_height:
        layout.append(("unused", page_height - current_y, set()))

    return layout


def display_vertical_layout_table(layout: List[Tuple[str, float, Set[str]]]) -> None:
    # Adjusted constants for table formatting
    TABLE_HEADER = "    ┌─────┬────────────┬────────────┬──────────────────────────────────────────┐"
    TABLE_ROW_FORMAT = "    │ {item:3d} │ {unused:10.2f} │ {used:10.2f} │ {fonts:40} │"
    TABLE_FOOTER = "    └─────┴────────────┴────────────┴──────────────────────────────────────────┘"

    print("  Vertical layout:")
    print(TABLE_HEADER)
    print(
        "    │ Item│    Unused  │     Used   │ Font Combinations                        │"
    )
    print(
        "    ├─────┼────────────┼────────────┼──────────────────────────────────────────┤"
    )

    combined_rows = []
    i = 0
    while i < len(layout):
        unused = 0.0
        used = 0.0
        fonts = set()

        # Handle unused section
        if i < len(layout) and layout[i][0] == "unused":
            unused = layout[i][1]
            i += 1

        # Handle subsequent used section
        if i < len(layout) and layout[i][0] == "used":
            used = layout[i][1]
            fonts = layout[i][2]
            i += 1

        combined_rows.append((unused, used, fonts))

    # Filter out entries with both zero unused and used
    filtered_rows = [row for row in combined_rows if row[0] > 0 or row[1] > 0]

    for idx, (unused, used, fonts) in enumerate(filtered_rows, 1):
        # Round font sizes to the nearest 0.5 pt
        rounded_fonts = {
            f"{font.split()[0]} {round(float(font.split()[1]) * 2) / 2:.1f}"
            for font in fonts
        }
        fonts_str = ", ".join(sorted(rounded_fonts)) if rounded_fonts else "-"
        print(
            TABLE_ROW_FORMAT.format(
                item=idx,
                unused=unused,
                used=used,
                fonts=fonts_str[:40],  # Truncate to fit column width
            )
        )

    print(TABLE_FOOTER)


def process_page(page: Dict, font_collector: FontCollector, show_table: bool):
    page_num = page["page_number"]
    width = page["width"]
    height = page["height"]

    print(f"\nPage {page_num}:")
    print(f"  Page size: {width:.2f} x {height:.2f}")

    # Process blocks
    filtered_blocks = []
    for block in page["blocks"]:
        ignore, partial = process_block(block, font_collector)
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
        for i, (typ, size, fonts) in enumerate(layout, 1):
            print(
                f"    {i:2d}. {typ.capitalize():6} {size:7.2f}  Fonts: {', '.join(sorted(fonts)) if fonts else '-'}"
            )


def process_and_save_files(
    data: List[Dict], output_dir: str, input_path: str, pages_to_process: List[int]
):
    os.makedirs(output_dir, exist_ok=True)
    base_name = os.path.splitext(os.path.basename(input_path))[0]

    sorted_data = []
    filtered_data = []

    for page in data:
        # Create sorted version
        sorted_page = page.copy()
        sorted_page["blocks"] = sorted(page["blocks"], key=lambda b: b["bbox"]["top"])
        sorted_data.append(sorted_page)

        # Create filtered version
        if page["page_number"] in pages_to_process or "all" in pages_to_process:
            filtered_page = sorted_page.copy()
            filtered_blocks = []

            for block in sorted_page["blocks"]:
                ignore, _ = process_block(block, FontCollector())  # Use dummy collector
                if not ignore:
                    filtered_blocks.append(block)

            filtered_page["blocks"] = filtered_blocks
            filtered_data.append(filtered_page)
        else:
            filtered_data.append(sorted_page)

    # Save files
    with open(os.path.join(output_dir, f"{base_name}_sorted.json"), "w") as f:
        json.dump(sorted_data, f, indent=2)

    with open(os.path.join(output_dir, f"{base_name}_filtered.json"), "w") as f:
        json.dump(filtered_data, f, indent=2)


def main():
    parser = argparse.ArgumentParser(description="PDF Layout Analyzer")
    parser.add_argument("file_path", help="Input JSON file")
    parser.add_argument(
        "-p", "--pages", default="all", help="Pages to process (e.g., '1-3,5', 'all')"
    )
    parser.add_argument(
        "-t", "--text-view", action="store_true", help="Display vertical layout as text"
    )
    parser.add_argument(
        "-o", "--output", default="layout_output", help="Output directory"
    )
    args = parser.parse_args()

    # Load data
    with open(args.file_path) as f:
        data = json.load(f)

    # Process pages
    pages_to_process = parse_page_range(args.pages)
    if "all" in pages_to_process:
        pages_to_process = [p["page_number"] for p in data]

    font_collector = FontCollector()

    for page in data:
        page_num = page["page_number"]
        if page_num in pages_to_process:
            font_collector.reset_page()
            process_page(page, font_collector, not args.text_view)

    # Save processed files
    process_and_save_files(data, args.output, args.file_path, pages_to_process)

    # Print combined fonts
    print("\nCombined fonts across all processed pages:")
    for font in sorted(font_collector.combined_fonts):
        print(f"  - {font}")


if __name__ == "__main__":
    main()
