import os
from blocks.utils import rect_to_dict


def extract_images(doc, output_dir):
    images = []
    doc_image_index = 0
    locations = {}

    for page_num, page in enumerate(doc, 1):
        page_images = []
        # Extract images
        image_list = page.get_images(full=True)
        for img_index, img in enumerate(image_list, 1):
            xref = img[0]
            base_image = doc.extract_image(xref)
            image_bytes = base_image["image"]
            image_filename = f"new_image_p{page_num}_{img_index}.png"
            image_path = os.path.join(output_dir, image_filename)
            with open(image_path, "wb") as image_file:
                image_file.write(image_bytes)
            images.append(image_filename)
            location_record = {
                "page": page_num,
                "page_index": img_index,
                "doc_index":  doc_image_index,
                "bbox": rect_to_dict(page.get_image_bbox(img)),
                "file": image_filename
            }
            doc_image_index += 1
            page_images.append(location_record)

        locations[page_num] = {'images':  page_images}

    return images, locations
