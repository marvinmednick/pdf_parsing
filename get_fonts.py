import pdfplumber
import argparse
from collections import defaultdict

# Function to set up argument parser
def setup_argparse():
    parser = argparse.ArgumentParser(description='Process a PDF file to extract font sizes and text.')
    parser.add_argument('filename', type=str, help='the filename of the PDF document')
    return parser

# Set up argument parser
parser = setup_argparse()
args = parser.parse_args()

# Dictionary to store line and partial line counts for each font-size combination
font_size_counts = defaultdict(lambda: {'lines': 0, 'partial_lines': 0})

# Open the PDF document
with pdfplumber.open(args.filename) as pdf:
    # Iterate through each page
    for page_number, page in enumerate(pdf.pages, start=1):
        # Print page divider
        print(f"------------- Page {page_number} -----------------")
        
        # Extract text lines
        lines = page.extract_text().split('\n')
        
        # Iterate through each line
        for line_number, line in enumerate(lines, start=1):
            # Extract characters for the line
            chars = page.chars
            
            # Filter characters that belong to the current line
            line_chars = [char for char in chars if char['top'] >= line_number * 10 and char['top'] < (line_number + 1) * 10]
            
            # Initialize current font-size and text
            current_font_size = None
            current_text = ""
            line_font_sizes = set()

            # Print line number
            print(f"Line {line_number}:")
            
            # Iterate through characters in the line
            for char in line_chars:
                font_size = round(char['size'], 1)
                font_name = char.get('fontname', 'Unknown')
                font_size_key = (font_name, font_size)
                text = char['text']
                
                # Determine if the text is whitespace
                is_whitespace = text.isspace()
                
                # Check if the font-size has changed, ignoring whitespace
                if font_size_key != current_font_size and not is_whitespace:
                    # Print the current text if it's not empty and current_font_size is not None
                    if current_text and current_font_size is not None:
                        display_text = current_text.strip() if current_text.strip() else "<<blank>>"
                        print(f"    Font {current_font_size[0]}, Size {current_font_size[1]} (len {len(current_text)}): {display_text}")
                        
                        # Update line font-sizes if the text is not blank
                        if display_text != "<<blank>>":
                            line_font_sizes.add(current_font_size)
                    
                    # Update the current font-size and text
                    current_font_size = font_size_key
                    current_text = text
                else:
                    # Add the text to the current text
                    current_text += text
            
            # Print the last text block in the line if current_font_size is not None
            if current_text and current_font_size is not None:
                display_text = current_text.strip() if current_text.strip() else "<<blank>>"
                # Determine if the line is a single font-size line
                font_indicator = "FL" if len(line_font_sizes) == 0 or (len(line_font_sizes) == 1 and not is_whitespace) else "  "
                print(f"    Font {current_font_size[0]}, Size {current_font_size[1]} {font_indicator} (len {len(current_text)}): {display_text}")
                
                # Update line font-sizes if the text is not blank
                if display_text != "<<blank>>":
                    line_font_sizes.add(current_font_size)
            
            # Update font-size counts
            for font_size_key in line_font_sizes:
                font_size_counts[font_size_key]['lines'] += 1
            if len(line_font_sizes) > 1:
                for font_size_key in line_font_sizes:
                    font_size_counts[font_size_key]['partial_lines'] += 1
            
            print()  # Empty line for better readability

# Print summary table
print("Summary Table:")
print(f"{'Font':<30}{'Size':<10}{'Lines':<10}{'Partial Lines':<15}")
for (font, size), counts in sorted(font_size_counts.items()):
    print(f"{font:<30}{size:<10}{counts['lines']:<10}{counts['partial_lines']:<15}")
