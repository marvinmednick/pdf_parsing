import json
import argparse
import os
from typing import List, Tuple, Dict, Any, Set
from collections import defaultdict
import csv


# Column width constants
ITEM_COLUMN_WIDTH = 5
UNUSED_COLUMN_WIDTH = 12
USED_COLUMN_WIDTH = 12
FONT_COLUMN_WIDTH = 40  # Reduced from 40
TEXT_COLUMN_WIDTH = 60  # New text column
COLUMN_PADDING = 1
COL_PAD = " " * COLUMN_PADDING
LEFT_INDENT = " " * 4

# Table format strings
TABLE_HEADER = f"{LEFT_INDENT}┌{'─' * (ITEM_COLUMN_WIDTH + 2 * COLUMN_PADDING)}┬{'─' * (UNUSED_COLUMN_WIDTH + 2 * COLUMN_PADDING)}┬{'─' * (USED_COLUMN_WIDTH + 2 * COLUMN_PADDING)}┬{'─' * (FONT_COLUMN_WIDTH + 2 * COLUMN_PADDING)}┬{'─' * (TEXT_COLUMN_WIDTH + 2 * COLUMN_PADDING)}┐"
HEADER_ROW = f"{LEFT_INDENT}│{'Item':^{ITEM_COLUMN_WIDTH + 2 * COLUMN_PADDING}}│{'Unused':^{UNUSED_COLUMN_WIDTH + 2 * COLUMN_PADDING}}│{'Used':^{USED_COLUMN_WIDTH + 2 * COLUMN_PADDING}}│{'Font Combinations':<{FONT_COLUMN_WIDTH + 2 * COLUMN_PADDING}}│{'Text Preview':<{TEXT_COLUMN_WIDTH + 2 * COLUMN_PADDING}}│"
HEADER_DIV = f"{LEFT_INDENT}├{'─' * (ITEM_COLUMN_WIDTH + 2 * COLUMN_PADDING)}┼{'─' * (UNUSED_COLUMN_WIDTH + 2 * COLUMN_PADDING)}┼{'─' * (USED_COLUMN_WIDTH + 2 * COLUMN_PADDING)}┼{'─' * (FONT_COLUMN_WIDTH + 2 * COLUMN_PADDING)}┼{'─' * (TEXT_COLUMN_WIDTH + 2 * COLUMN_PADDING)}┤"
TABLE_ROW = f"{LEFT_INDENT}│{{item:^{ITEM_COLUMN_WIDTH + 2 * COLUMN_PADDING}}}│{{unused:^{UNUSED_COLUMN_WIDTH + 2 * COLUMN_PADDING}.2f}}│{{used:^{USED_COLUMN_WIDTH + 2 * COLUMN_PADDING}.2f}}│{{font:<{FONT_COLUMN_WIDTH + 2 * COLUMN_PADDING}}}│{{text:<{TEXT_COLUMN_WIDTH + 2 * COLUMN_PADDING}}}│"
BLANK_ROW = f"{LEFT_INDENT}│{' ' * (ITEM_COLUMN_WIDTH + 2 * COLUMN_PADDING)}│{' ' * (UNUSED_COLUMN_WIDTH + 2 * COLUMN_PADDING)}│{' ' * (USED_COLUMN_WIDTH + 2 * COLUMN_PADDING)}│{{font:<{FONT_COLUMN_WIDTH + 2 * COLUMN_PADDING}}}│{' ' * (TEXT_COLUMN_WIDTH + 2 * COLUMN_PADDING)}│"
TABLE_FOOTER = f"{LEFT_INDENT}└{'─' * (ITEM_COLUMN_WIDTH + 2 * COLUMN_PADDING)}┴{'─' * (UNUSED_COLUMN_WIDTH + 2 * COLUMN_PADDING)}┴{'─' * (USED_COLUMN_WIDTH + 2 * COLUMN_PADDING)}┴{'─' * (FONT_COLUMN_WIDTH + 2 * COLUMN_PADDING)}┴{'─' * (TEXT_COLUMN_WIDTH + 2 * COLUMN_PADDING)}┘"


class FontProcessor:
    def __init__(self):
        self.font_registry = {}  # base_name -> font_id
        self.font_details = {}  # font_id -> (name, foundry, style)
        self.font_instances = set()  # (font_id, style, size)
        self.current_page_instances = set()
        self.next_font_id = 1

    def _round_size(self, size: float) -> float:
        """Round to nearest 0.5pt"""
        return round(size * 2) / 2

    def _parse_font_name(self, font: str) -> tuple:
        """Parse font name into (base_name, style, foundry)"""
        foundry = "Other"
        if font.endswith("MT"):
            foundry = "MonoType"
            font = font[:-2].rstrip("-")

        if "-" in font:
            parts = font.rsplit("-", 1)
            return (parts[0], parts[1], foundry)
        return (font, "Regular", foundry)

    def add_font(self, font: str, size: float):
        """Register font with style/size without storing style in registry"""
        if not font or not size:
            return

        rounded_size = self._round_size(size)
        base_name, style, foundry = self._parse_font_name(font)

        if base_name not in self.font_registry:
            self.font_registry[base_name] = self.next_font_id
            self.font_details[self.next_font_id] = {  # Removed style
                "name": base_name,
                "foundry": foundry,
            }
            self.next_font_id += 1

        font_id = self.font_registry[base_name]
        self.font_instances.add((font_id, style, rounded_size))

    def reset_page(self):
        """Reset page-specific font tracking"""
        self.current_page_instances = set()

    def format_font_entry(self, font_id: int, style: str, size: float) -> str:
        """Use passed style parameter instead of stored value"""
        details = self.font_details.get(font_id, {"name": "Unknown", "foundry": ""})
        return f"f{font_id} - {details['name']:20} {style:10} {size:.1f}"  # Use parameter, not details

    def get_sorted_font_list(self):
        """Group by font_id and style from instances"""
        style_map = defaultdict(lambda: defaultdict(set))

        for font_id, style, size in self.font_instances:
            style_map[font_id][style].add(size)

        sorted_fonts = []
        for font_id in sorted(self.font_registry.values()):
            base_name = self.font_details[font_id]["name"]
            for style in sorted(style_map[font_id]):
                sizes = sorted(style_map[font_id][style])
                size_str = ", ".join(f"{s:.1f}" for s in sizes)
                sorted_fonts.append((font_id, base_name, style, size_str))

        return sorted_fonts


def parse_page_range(page_range: str, exclude_pages: str = "") -> List[int]:
    """Parse page range string into list of page numbers, considering exclusions."""
    if page_range.lower() == "all":
        pages = ["all"]
    else:
        pages = []
        for part in page_range.replace(" ", "").split(","):
            if "-" in part:
                start, end = map(int, part.split("-"))
                pages.extend(range(start, end + 1))
            else:
                pages.append(int(part))

    # Handle exclusions
    if exclude_pages:
        exclude = set()
        for part in exclude_pages.replace(" ", "").split(","):
            if "-" in part:
                start, end = map(int, part.split("-"))
                exclude.update(range(start, end + 1))
            else:
                exclude.add(int(part))
        pages = [p for p in pages if p not in exclude]

    return pages


def is_text_segment_empty(segment: Dict[str, Any]) -> bool:
    """Check if a text segment is empty or invalid"""
    return (
        not segment.get("text", "").strip()
        or segment.get("font") is None
        or segment.get("font_size") is None
    )


def process_block(
    block: Dict[str, Any], font_processor: FontProcessor
) -> Tuple[bool, bool]:
    text_segments = block.get("text_segments", [])
    if not text_segments:
        return True, False

    all_empty = True
    some_empty = False

    for seg in text_segments:
        # Collect font information even from empty segments
        if seg.get("font") and seg.get("font_size"):
            font_processor.add_font(seg["font"], seg["font_size"])

        empty = is_text_segment_empty(seg)
        if not empty:
            all_empty = False
        else:
            some_empty = True

    return all_empty, (some_empty and not all_empty)


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
) -> List[Tuple[str, float, Set[tuple], str]]:  # Changed return type
    """Analyze vertical layout with text aggregation for same-font blocks"""
    layout = []
    current_y = 0.0
    sorted_blocks = sorted(blocks, key=lambda b: b["bbox"]["top"])
    current_text = ""
    current_font = None

    for block in sorted_blocks:
        bbox = block["bbox"]
        block_fonts = set()
        block_text = []

        for seg in block.get("text_segments", []):
            if seg.get("font") and seg.get("font_size"):
                font_key = (seg["font"], seg["font_size"])
                block_fonts.add(font_key)
                if font_key == current_font:
                    current_text += seg.get("text", "") + " "
                else:
                    current_font = font_key
                    current_text = seg.get("text", "") + " "
            elif seg.get("text"):
                block_text.append(seg["text"])

        # Add unused space entry with empty text
        layout.append(("unused", bbox["top"] - current_y, set(), ""))

        # Add used space with fonts and collected text
        layout.append(
            ("used", bbox["bottom"] - bbox["top"], block_fonts, current_text.strip())
        )
        current_y = bbox["bottom"]
        current_text = ""  # Reset for next block

    if current_y < page_height:
        layout.append(("unused", page_height - current_y, set(), ""))

    return layout


def display_vertical_layout_table(
    layout: List[Tuple[str, float, Set[tuple], str]], font_processor: FontProcessor
):
    print(" Vertical layout:")
    print(TABLE_HEADER)
    print(HEADER_ROW)
    print(HEADER_DIV)

    combined_rows = []
    i = 0
    while i < len(layout):
        unused = 0.0
        used = 0.0
        fonts = set()
        text = ""

        if i < len(layout) and layout[i][0] == "unused":
            unused = max(0.0, float(layout[i][1]))
            i += 1

        if i < len(layout) and layout[i][0] == "used":
            used = max(0.0, float(layout[i][1]))
            fonts = set()
            for font_name, size in layout[i][2]:
                base_name, style, _ = font_processor._parse_font_name(font_name)
                rounded_size = font_processor._round_size(size)
                font_id = font_processor.font_registry.get(base_name, -1)
                fonts.add((font_id, style, rounded_size))
            text = layout[i][3][:TEXT_COLUMN_WIDTH]  # Truncate text
            i += 1

        if unused > 0 or used > 0 or fonts:
            combined_rows.append((unused, used, fonts, text))

    for idx, (unused, used, fonts, text) in enumerate(combined_rows, 1):
        font_entries = []
        for font_id, style, size in fonts:
            font_entries.append(font_processor.format_font_entry(font_id, style, size))

        truncated_text = (
            (text[: TEXT_COLUMN_WIDTH - 3] + "...")
            if len(text) > TEXT_COLUMN_WIDTH
            else text
        )

        if not font_entries:
            print(
                TABLE_ROW.format(
                    item=idx, unused=unused, used=used, font="-", text=truncated_text
                )
            )
        else:
            print(
                TABLE_ROW.format(
                    item=idx,
                    unused=unused,
                    used=used,
                    font=font_entries[0],
                    text=truncated_text,
                )
            )
            for font in font_entries[1:]:
                print(BLANK_ROW.format(font=font))

    print(TABLE_FOOTER)


def process_page(page: Dict, font_processor: FontProcessor, show_table: bool):
    """Process and display information for a single page"""
    font_processor.reset_page()
    page_num = page["page_number"]
    width = page["width"]
    height = page["height"]
    blocks = page["blocks"]

    print(f"\nPage {page_num}:")
    print(f"  Page size: {width:.2f} x {height:.2f}")

    # Process blocks
    filtered_blocks = []
    for block in blocks:
        ignore, partial = process_block(block, font_processor)
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
        display_vertical_layout_table(layout, font_processor)
    else:
        print("\n  Vertical layout:")
        for i, (typ, size, fonts) in enumerate(layout, 1):
            print(f"    {i:2d}. {typ.capitalize():6} {size:7.2f}")


def process_and_save_files(
    data: List[Dict], output_dir: str, input_path: str, pages_to_process: List[int]
):
    """Generate and save sorted/filtered JSON files"""
    os.makedirs(output_dir, exist_ok=True)
    base_name = os.path.splitext(os.path.basename(input_path))[0]

    sorted_data = []
    filtered_data = []

    for page in data:
        # Create sorted version (always sorted)
        sorted_page = page.copy()
        sorted_page["blocks"] = sorted(page["blocks"], key=lambda b: b["bbox"]["top"])
        sorted_data.append(sorted_page)

        # Create filtered version (only for processed pages)
        if page["page_number"] in pages_to_process or "all" in pages_to_process:
            filtered_page = sorted_page.copy()
            filtered_blocks = []

            for block in sorted_page["blocks"]:
                ignore, _ = process_block(block, FontProcessor())  # Dummy processor
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


def generate_summary(data: List[Dict], pages_to_process: List[int]) -> None:
    """Generate and display a summary of processed pages."""
    total_blocks = 0
    total_fonts = set()
    unused_space = 0

    for page in data:
        if page["page_number"] in pages_to_process or "all" in pages_to_process:
            blocks = page.get("blocks", [])
            total_blocks += len(blocks)
            for block in blocks:
                for segment in block.get("text_segments", []):
                    font = segment.get("font")
                    if font:
                        total_fonts.add(font)
                    unused_space += block.get("bbox", {}).get("x0", 0)

    print("\nSummary:")
    print(f" Total Pages Processed: {len(pages_to_process)}")
    print(f" Total Blocks Processed: {total_blocks}")
    print(f" Unique Fonts Used: {len(total_fonts)}")
    print(f" Total Unused Space (approx.): {unused_space:.2f}")


def main():
    parser = argparse.ArgumentParser(description="PDF Layout Analyzer")
    parser.add_argument("file_path", help="Input JSON file")
    parser.add_argument(
        "-p", "--pages", default="all", help="Pages to process (e.g., '1-3,5', 'all')"
    )
    parser.add_argument(
        "-t",
        "--text-view",
        action="store_true",
        help="Display vertical layout as text instead of table",
    )
    parser.add_argument(
        "-o", "--output", default="layout_output", help="Output directory"
    )
    parser.add_argument(
        "--exclude-pages",
        default="",
        help="Pages to exclude from processing (e.g., '2-4')",
    )

    args = parser.parse_args()

    # Load data
    with open(args.file_path) as f:
        data = json.load(f)

    # Process pages
    pages_to_process = parse_page_range(args.pages, args.exclude_pages)
    if "all" in pages_to_process:
        pages_to_process = [p["page_number"] for p in data]

    font_processor = FontProcessor()

    # Process and display pages
    for page in data:
        if page["page_number"] in pages_to_process:
            process_page(page, font_processor, not args.text_view)

    # Save processed files
    process_and_save_files(data, args.output, args.file_path, pages_to_process)
    print(f"\nOutput files saved to: {args.output}")

    # Print combined font list
    print("\nFont Summary:")
    print(
        "┌──────┬─────────────────────────────┬──────────────┬──────────────────────────────────────────────┐"
    )
    print(
        "│  ID  │ Font Name                   │ Style        │ Sizes Used (pt)                              │"
    )
    print(
        "├──────┼─────────────────────────────┼──────────────┼──────────────────────────────────────────────┤"
    )

    for font_id, name, style, sizes in font_processor.get_sorted_font_list():
        print(f"│ {font_id:4} │ {name:27} │ {style:12} │ {sizes:44} │")

    print(
        "└──────┴─────────────────────────────┴──────────────┴──────────────────────────────────────────────┘"
    )

    generate_summary(data, pages_to_process)


if __name__ == "__main__":
    main()
