import json
import argparse
from typing import Dict, List


def process_json_file(file_path: str) -> None:
    with open(file_path, "r") as file:
        data = json.load(file)

    for page in data:
        page_number = page["page_number"]
        width = page["width"]
        height = page["height"]
        blocks = page["blocks"]

        # Initialize margins with extreme values
        left_margin = width
        right_margin = 0
        top_margin = height
        bottom_margin = 0

        # Find the margins and used area
        for block in blocks:
            bbox = block["bbox"]
            left_margin = min(left_margin, bbox["x0"])
            right_margin = max(right_margin, bbox["x1"])
            top_margin = min(top_margin, bbox["top"])
            bottom_margin = max(bottom_margin, bbox["bottom"])

        # Calculate used area
        used_area = {
            "x0": left_margin,
            "x1": right_margin,
            "top": top_margin,
            "bottom": bottom_margin,
        }

        # Display results
        print(f"Page {page_number}:")
        print(f"  Page size: {width} x {height}")
        print("  Margins:")
        print(f"    Left: 0 to {left_margin}")
        print(f"    Right: {right_margin} to {width}")
        print(f"    Top: 0 to {top_margin}")
        print(f"    Bottom: {bottom_margin} to {height}")
        print("  Used area:")
        print(f"    x0: {used_area['x0']}, x1: {used_area['x1']}")
        print(f"    top: {used_area['top']}, bottom: {used_area['bottom']}")
        print()


def main():
    parser = argparse.ArgumentParser(
        description="Process JSON file and display page information"
    )
    parser.add_argument("file_path", help="Path to the JSON file")
    args = parser.parse_args()

    process_json_file(args.file_path)


if __name__ == "__main__":
    main()
