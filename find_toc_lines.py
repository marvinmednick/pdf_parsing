import json
import re
import argparse

def load_config(config_file):
    with open(config_file, 'r') as file:
        return json.load(file)

def build_regex(config_section):
    # Extract configuration settings
    types = config_section.get("types", [])
    section_number_pattern = config_section.get("section_number_pattern", "\\d+(?:\\.\\d+)*")
    page_number_pattern = config_section.get("page_number_pattern", "\\d+")
    
    # Build the regex pattern
    type_pattern = '|'.join(re.escape(t) for t in types)
    toc_pattern = (
        rf'(?:(?P<type>{type_pattern})?\.?\s*'
        rf'(?P<number>{section_number_pattern}))?\s*'
        rf'(?P<title>.*?)\s*'
        rf'(?:\.{{2,}}|…|\s{{2,}})\s*'
        rf'(?P<page>{page_number_pattern})'
    )
    
    return toc_pattern

def process_file(file_name, regex_pattern):
    with open(file_name, 'r') as file:
        for line in file:
            line = line.strip()
            match = regex_pattern.match(line)
            if match:
                type_str = match.group("type") or ""
                number_str = match.group("number") or ""
                title_str = match.group("title")
                page_str = match.group("page")
                print(f"{type_str:<10} {number_str:<10} {page_str:<5} {title_str}")

def main():
    parser = argparse.ArgumentParser(description='Process a file using a configurable regex pattern.')
    parser.add_argument('file_name', help='the file to process')
    parser.add_argument('--section', help='the configuration section to use (default: standard)')
    args = parser.parse_args()
    
    config = load_config('config.json')
    default_section = config.get("default_section", "standard")
    section_name = args.section or default_section
    config_section = config["sections"].get(section_name)
    
    if config_section is None:
        print(f"Error: Configuration section '{section_name}' not found.")
        return
    
    regex_pattern = re.compile(build_regex(config_section))
    process_file(args.file_name, regex_pattern)

if __name__ == "__main__":
    main()
