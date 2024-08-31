import argparse
import os
import fitz  # PyMuPDF
import pdfplumber
from PIL import Image, ImageDraw, ImageFont

def visualize_layout(pdf_path, output_dir, header_height, footer_height):
    os.makedirs(output_dir, exist_ok=True)

    with pdfplumber.open(pdf_path) as pdf:
        for page_num, page in enumerate(pdf.pages):
            # Create a blank image
            img = Image.new('RGB', (int(page.width), int(page.height)), color='white')
            draw = ImageDraw.Draw(img)

            # Draw header area
            draw.rectangle([0, 0, page.width, header_height], outline="red", width=2)
            draw.text((10, 10), "Header", fill="red")

            # Draw footer area
            draw.rectangle([0, page.height - footer_height, page.width, page.height], outline="blue", width=2)
            draw.text((10, page.height - footer_height + 10), "Footer", fill="blue")

            # Extract text with precise coordinates
            text_objects = page.extract_words(x_tolerance=3, y_tolerance=3, keep_blank_chars=True)

            main_content_text = []
            current_line_y = None
            current_line = []

            for obj in text_objects:
                if header_height < obj['top'] < (page.height - footer_height):
                    draw.rectangle([obj['x0'], obj['top'], obj['x1'], obj['bottom']], outline="green")
                    draw.text((obj['x0'], obj['top'] - 10), obj['text'][:10], fill="green", font=ImageFont.load_default())
                    
                    if current_line_y is None or abs(obj['top'] - current_line_y) > 5:  # New line
                        if current_line:
                            main_content_text.append(" ".join(current_line))
                        current_line = [obj['text']]
                        current_line_y = obj['top']
                    else:
                        current_line.append(obj['text'])

            # Add the last line
            if current_line:
                main_content_text.append(" ".join(current_line))

            # Save the image
            img.save(os.path.join(output_dir, f"page_{page_num + 1}_layout.png"))

            # Save extracted text
            text_content = "\n".join(main_content_text)
            with open(os.path.join(output_dir, f"page_{page_num + 1}_text.txt"), "w", encoding="utf-8") as text_file:
                text_file.write(text_content)

            print(f"Processed page {page_num + 1}")

    print("Processing complete. Check the output directory for results.")

def main():
    parser = argparse.ArgumentParser(description="Visualize PDF layout and text objects")
    parser.add_argument("filename", help="Input PDF file")
    parser.add_argument("--header", type=float, default=50, help="Header height in points")
    parser.add_argument("--footer", type=float, default=50, help="Footer height in points")
    args = parser.parse_args()

    pdf_path = args.filename
    base_name = os.path.splitext(os.path.basename(pdf_path))[0]
    output_dir = os.path.join("layout_visualization", base_name)
    
    visualize_layout(pdf_path, output_dir, args.header, args.footer)

if __name__ == "__main__":
    main()
