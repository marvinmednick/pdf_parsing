import json
import re


def process_toc(toc_data, toc_file_path, toc_parsing_config, regex_pattern):
    toc_entries = []

    for page_data in toc_data:
        page_number = page_data["page_number"]

        for block in page_data["blocks"]:
            for segment in block["text_segments"]:
                text = segment["text"].strip()
                lines = text.splitlines()
                for line in lines:
                    match = regex_pattern.match(line)
                    if match:
                        entry = {}
                        for group in toc_parsing_config['regex_groups']:
                            if isinstance(toc_parsing_config[group], dict):
                                entry[group] = match.group(group)
                            else:
                                entry[group] = match.group(group)
                        entry['page_number'] = page_number
                        toc_entries.append(entry)
                    else:
                        print(f"No Match {line}")

    with open(toc_file_path, 'w', encoding='utf-8') as f:
        json.dump(toc_entries, f, ensure_ascii=False, indent=4)

    return toc_entries
