def normalize_bbox(bbox):
    if isinstance(bbox, tuple):
        # Unpack the tuple values
        x0, top, x1, bottom = bbox
        # Create and return the normalized dictionary
        return {'x0': x0, 'top': top, 'x1': x1, 'bottom': bottom}
    elif isinstance(bbox, dict):
        if 'y0' in bbox:
            return {'x0': bbox['x0'], 'top': bbox['y0'], 'x1': bbox['x1'], 'bottom': bbox['y1']}
        else:
            return bbox
    else:
        raise ValueError('Bbox must be a tuple or dictionary.')


def rect_to_dict(rect):
    if isinstance(rect, tuple) and len(rect) == 4:
        return {"x0": rect[0], "top": rect[1], "x1": rect[2], "bottom": rect[3]}
    elif hasattr(rect, 'x0'):
        return {"x0": rect.x0, "top": rect.y0, "x1": rect.x1, "bottom": rect.y1}
    else:
        raise ValueError("Unexpected rect format")


def parse_page_ranges(page_ranges, total_pages, default_range=None):
    if not page_ranges:
        return default_range if default_range is not None else list(range(1, total_pages + 1))

    pages = []
    for page_range in page_ranges.split(","):
        if "-" in page_range:
            start, end = page_range.split("-")
            start = int(start) if start else 1
            end = int(end) if end else total_pages
            pages.extend(range(start, end + 1))
        else:
            pages.append(int(page_range))
    return pages
