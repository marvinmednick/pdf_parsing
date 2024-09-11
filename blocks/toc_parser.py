import json
import re


def parse_toc(toc_data, toc_parsing_config):
    if toc_parsing_config is None:
        toc_parsing_config = {}

    entry_regex = re.compile(toc_parsing_config.get('entry_regex', '^((?:\\d+\\.)+)\\s+(.+)\\s+(\\d+)$'))
    entry_fields = toc_parsing_config.get('entry_fields', [
        {'name': 'section_number', 'group': 1},
        {'name': 'title', 'group': 2},
        {'name': 'page_number', 'group': 3}
    ])

    toc_entries = []

    for page_data in toc_data:
        page_number = page_data["page_number"]

        for block in page_data["blocks"]:
            for segment in block["text_segments"]:
                text = segment["text"].strip()
                print(f"Examining {text}")

                if text.startswith(("Table of Contents", "Contents")):
                    continue

                match = entry_regex.match(text)
                if match:
                    entry = {}
                    for field in entry_fields:
                        group = field['group']
                        if isinstance(group, list):
                            for g in group:
                                if match.group(g):
                                    entry[field['name']] = match.group(g)
                                    break
                        else:
                            entry[field['name']] = match.group(group)
                    entry['page_number'] = page_number
                    toc_entries.append(entry)

    return toc_entries


def process_toc(toc_data, toc_file_path, toc_parsing_config):
    toc_entries = parse_toc(toc_data, toc_parsing_config)

    with open(toc_file_path, 'w', encoding='utf-8') as f:
        json.dump(toc_entries, f, ensure_ascii=False, indent=4)

    return toc_entries
