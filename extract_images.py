import argparse
import fitz  # PyMuPDF
import os

def extract_images(pdf_path):
    # Open the PDF document
    doc = fitz.open(pdf_path)

    # Create a directory to store the extracted images
    output_dir = "extracted_images"
    os.makedirs(output_dir, exist_ok=True)

    # Iterate through each page in the PDF
    for page_num in range(len(doc)):
        page = doc[page_num]
        
        # Get a list of image objects on the page
        image_list = page.get_images(full=True)
        
        # Iterate through each image on the page
        for img_index, img in enumerate(image_list):
            xref = img[0]
            base_image = doc.extract_image(xref)
            image_bytes = base_image["image"]
            
            # Get the bounding box of the image
            bbox = page.get_image_bbox(img)
            
            # Generate a unique filename for the image
            image_filename = f"image_page{page_num + 1}_{img_index + 1}.png"
            image_path = os.path.join(output_dir, image_filename)
            
            # Save the image
            with open(image_path, "wb") as image_file:
                image_file.write(image_bytes)
            
            # Print information about the extracted image
            print(f"Image extracted: {image_filename}")
            print(f"Page: {page_num + 1}")
            print(f"Bounding Box: {bbox}")
            print("--------------------")

    # Close the PDF document
    doc.close()

def main():
    parser = argparse.ArgumentParser(description="Extract images from a PDF document")
    parser.add_argument("pdf_file", help="Path to the PDF file")
    args = parser.parse_args()

    extract_images(args.pdf_file)

if __name__ == "__main__":
    main()
