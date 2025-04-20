import pdfplumber
import argparse
import sys

# Set up argument parser
parser = argparse.ArgumentParser(description='Search for text in a PDF file.')
parser.add_argument('pdf_file', type=str, help='Path to the PDF file')

# Parse arguments
args = parser.parse_args()

# Function to search text in PDF
def search_text_in_pdf(pdf_file, search_text):
    matches = []
    with pdfplumber.open(pdf_file) as pdf:
        for page_number in range(len(pdf.pages)):
            page = pdf.pages[page_number]
            text = page.extract_text()  # Extract text from the page
            if text and search_text in text:
                for word in page.extract_words():
                    if search_text in word['text']:
                        matches.append((word['text'], word['x0'], word['top'], word['x1'], word['bottom']))  # Match found with bounding box coordinates
    return matches

# Open the PDF file
pdf = pdfplumber.open(args.pdf_file)

print(f"PDF '{args.pdf_file}' opened successfully.")
print("Enter search strings (press Ctrl+D to exit):")

# Loop for multiple searches
while True:
    try:
        # Prompt the user for the search string
        search_string = input("Search for: ")
        
        # Search for the string in the PDF
        results = search_text_in_pdf(args.pdf_file, search_string)

        # Print matches with bounding box coordinates
        if results:
            print(f"Found {len(results)} matches:")
            for match in results:
                text, x0, top, x1, bottom = match
                print(f'Matched text: "{text}", Bounding box: (x0: {x0}, top: {top}, x1: {x1}, bottom: {bottom})')
        else:
            print("No matches found.")
        
        print()  # Empty line for readability

    except EOFError:
        # Exit the loop when user presses Ctrl+D
        print("\nExiting the search.")
        break

# Close the PDF file
pdf.close()
