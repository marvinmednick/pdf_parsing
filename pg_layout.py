import json
import argparse
from typing import List, Tuple, Dict, Any

# Constants
TABLE_HEADER = "    ┌─────┬────────────┬────────────┐"
TABLE_ROW_FORMAT = "    │ {item:3d} │ {unused:10.2f} │ {used:10.2f} │"
TABLE_FOOTER = "    └─────┴────────────┴────────────┘"


def parse_page_range(page_range: str) -> List[int]:
    if page_range.lower() == "all":
        return ["all"]

    return [
        page
        for part in page_range.replace(" ", "").split(",")
        for page in (
            range(int(part.split("-")[0]), int(part.split("-")[1]) + 1)
            if "-" in part
            else [int(part)]
        )
    ]


def is_text_segment_empty(segment: Dict[str, Any]) -> bool:
    return (
        "text" not in segment
        or segment.get("text", "").strip() == ""
        or segment.get("font") is None
        or segment.get("font_size") is None
    )


def process_block(block: Dict[str, Any]) -> Tuple[bool, bool]:
    if "text_segments" not in block or not block.get("text_segments", []):
        return True, False

    text_segments = block["text_segments"]
    empty_segments = [is_text_segment_empty(segment) for segment in text_segments]

    if all(empty_segments):
        return True, False

    return False, any(empty_segments) and not all(empty_segments)


def find_margins(
    blocks: List[dict], width: float, height: float
) -> Tuple[float, float, float, float]:
    if not blocks:
        return 0, width, 0, height

    left_margin = min(block["bbox"]["x0"] for block in blocks)
    right_margin = max(block["bbox"]["x1"] for block in blocks)
    top_margin = min(block["bbox"]["top"] for block in blocks)
    bottom_margin = max(block["bbox"]["bottom"] for block in blocks)

    return left_margin, right_margin, top_margin, bottom_margin


def analyze_vertical_layout(
    blocks: List[dict], height: float
) -> List[Tuple[str, float]]:
    vertical_layout = []
    current_y = 0

    sorted_blocks = sorted(blocks, key=lambda b: b["bbox"]["top"])

    if not sorted_blocks:
        return [("unused", height)]

    for block in sorted_blocks:
        bbox = block["bbox"]
        if bbox["top"] > current_y:
            vertical_layout.append(("unused", bbox["top"] - current_y))
        vertical_layout.append(("used", bbox["bottom"] - bbox["top"]))
        current_y = bbox["bottom"]

    if current_y < height:
        vertical_layout.append(("unused", height - current_y))

    return vertical_layout


def display_margins_and_used_area(
    margins: Tuple[float, float, float, float], width: float, height: float
) -> None:
    left_margin, right_margin, top_margin, bottom_margin = margins
    print("  Margins:")
    print(f"    Left: 0 to {left_margin}")
    print(f"    Right: {right_margin} to {width}")
    print(f"    Top: 0 to {top_margin}")
    print(f"    Bottom: {bottom_margin} to {height}")
    print("  Used area:")
    print(f"    x0: {left_margin}, x1: {right_margin}")
    print(f"    top: {top_margin}, bottom: {bottom_margin}")


def display_vertical_layout(vertical_layout: List[Tuple[str, float]]) -> None:
    print("  Vertical layout:")
    for area_type, size in vertical_layout:
        print(f"    {area_type.capitalize()} area: {size:.2f}")


def display_vertical_layout_table(vertical_layout: List[Tuple[str, float]]) -> None:
    print("  Vertical layout:")
    print(TABLE_HEADER)
    print("    │ Item│    Unused  │     Used   │")
    print(TABLE_HEADER)

    unused_areas = [
        size for area_type, size in vertical_layout if area_type == "unused"
    ]
    used_areas = [size for area_type, size in vertical_layout if area_type == "used"]

    max_len = max(len(unused_areas), len(used_areas))
    unused_areas.extend([0] * (max_len - len(unused_areas)))
    used_areas.extend([0] * (max_len - len(used_areas)))

    for i in range(max_len):
        print(
            TABLE_ROW_FORMAT.format(
                item=i + 1, unused=unused_areas[i], used=used_areas[i]
            )
        )

    print(TABLE_FOOTER)


def process_page(page: Dict[str, Any], show_table: bool) -> None:
    page_number = page["page_number"]
    width = page["width"]
    height = page["height"]
    blocks = page["blocks"]

    print(f"Page {page_number}:")
    print(f"  Page size: {width} x {height}")

    filtered_blocks = []
    for block in blocks:
        ignore_block, has_partial_empty = process_block(block)
        if not ignore_block:
            filtered_blocks.append(block)
            if has_partial_empty:
                print(
                    f"  Block {block.get('blocknumber', 'unknown')}: part of the block included empty text"
                )

    margins = find_margins(filtered_blocks, width, height)
    display_margins_and_used_area(margins, width, height)

    vertical_layout = analyze_vertical_layout(filtered_blocks, height)

    if show_table:
        display_vertical_layout_table(vertical_layout)
    else:
        display_vertical_layout(vertical_layout)

    print()


def process_json_file(
    file_path: str, pages_to_process: List[int], show_table: bool = False
) -> None:
    with open(file_path, "r") as file:
        data = json.load(file)

    if pages_to_process == ["all"]:
        pages_to_process = range(1, len(data) + 1)

    for page in data:
        if page["page_number"] in pages_to_process:
            process_page(page, show_table)


def main():
    parser = argparse.ArgumentParser(
        description="Process JSON file and display page information"
    )
    parser.add_argument("file_path", help="Path to the JSON file")
    parser.add_argument(
        "-p",
        "--pages",
        default="1",
        help="Pages to process (e.g., '1-3,5,7-9' or 'all')",
    )
    parser.add_argument(
        "-t", "--table", action="store_true", help="Display vertical layout as a table"
    )
    args = parser.parse_args()

    pages_to_process = parse_page_range(args.pages)
    process_json_file(args.file_path, pages_to_process, args.table)


if __name__ == "__main__":
    main()
