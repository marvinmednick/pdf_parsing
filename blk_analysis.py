import argparse
import os
import yaml
import pymupdf
import json
import re
from blocks.pdf_processor import preprocess_pdf, analyze_pdf
from blocks.toc_parser import process_toc

def parse_arguments():
    """
    Parse command line arguments
    """
    parser = argparse.ArgumentParser(description='Process PDF to outline blocks and extract text details')
    parser.add_argument('input_file', help='Input PDF file')
    parser.add_argument('-o', '--output_file', help='Output PDF file')
    parser.add_argument('-ob', '--outline_blocks', action='store_true', help='Outline blocks in the PDF')
    parser.add_argument('-oit', '--outline_images_tables', action='store_true', help='Outline images and tables in the PDF')
    parser.add_argument('-ad', '--appdir', help='Application directory', default='pdf_blocks')
    parser.add_argument('-od', '--output_dir', help='Output directory')
    parser.add_argument('-hs', '--header_size', type=float, default=0.07, help='Header size as a percentage of the page height (e.g., 0.1 for 10%%)')
    parser.add_argument('-fs', '--footer_size', type=float, default=0.07, help='Footer size as a percentage of the page height (e.g., 0.1 for 10%%)')
    parser.add_argument('-main', '--main_pages', help='List of page ranges for the main document (e.g., "1-3,5,7-")')
    parser.add_argument('-exclude', '--exclude_pages', help='List of page ranges to exclude (e.g., "4,6,8-10")')
    parser.add_argument('-toc', '--toc_pages', help='List of page ranges for the table of contents (e.g., "2-3")')
    parser.add_argument('-cfg', '--config_file', help='Path to the YAML configuration file')
    parser.add_argument('-skip', '--skip_preprocessing', action='store_true', help='Skip the preprocessing phase and use the filtered data input file')
    parser.add_argument('--filtered_data_file', help='Path to the filtered data input file')
    parser.add_argument('-tcfg', '--toc_parsing_config', help='TOC parsing configuration to use from the global config file')
    parser.add_argument('-nf', '--nofiles', action='store_true', help='Do not save files at completion')
    return parser.parse_args()


def load_global_config(config_file):
    if os.path.exists(config_file):
        with open(config_file, 'r') as f:
            return yaml.safe_load(f)
    return {}


def build_regex(config_section):
    # Extract configuration settings
    regex_groups = config_section.get("regex_groups", [])

    # Build the regex pattern
    regex_parts = []
    for group in regex_groups:
        # check if group is in this this configuration, if not check the common regex config
        group_config = config_section.get(group)
        if group_config is None:
            raise ValueError(f"Configuration for group '{group}' not found")

        # if the group is a dict, proess the fields
        if isinstance(group_config, dict):
            group_regex = group_config.get('regex')
            group_required = group_config.get('required', False)

        # otherwise use the group as the regex string and marke as not required
        elif isinstance(group_config, str):
            group_regex = group_config
            group_required = False

        # Add this item to the regex
        if group_required:
            regex_parts.append(group_regex)
        else:
            regex_parts.append(f"({group_regex})?")

    toc_pattern = r''.join(regex_parts)

    return toc_pattern


def main():
    args = parse_arguments()

    global_config = load_global_config('config_blk_analysis.yaml')

    # Load configuration from YAML file if provided
    config = {}
    if args.config_file:
        with open(args.config_file, 'r') as f:
            config = yaml.safe_load(f)
        for key, value in config.items():
            setattr(args, key, value)

    common_regex = global_config.get('common_regex', {})

    toc_parsing_config = global_config.get('toc_parsing_configurations', {}).get(args.toc_parsing_config or 'default', {})
    toc_parsing_config = common_regex | toc_parsing_config

    output_dir = args.output_dir if args.output_dir else os.path.basename(args.input_file)[:-4]
    app_dir = args.appdir
    output_dir_path = os.path.join(app_dir, output_dir)
    os.makedirs(output_dir_path, exist_ok=True)

    output_file = args.output_file if args.output_file else os.path.join(output_dir_path, f"{os.path.basename(args.input_file)[:-4]}_outline.pdf")

    if args.skip_preprocessing:
        filtered_data_file = args.filtered_data_file if args.filtered_data_file else os.path.join(output_dir_path, f"filtered_{os.path.basename(args.input_file)[:-4]}_blocks.json")
        toc_data_file = os.path.join(output_dir_path, f"toc_{os.path.basename(args.input_file)[:-4]}_blocks.json")
        
        with open(filtered_data_file, 'r', encoding='utf-8') as f:
            filtered_pages_data = json.load(f)
        
        with open(toc_data_file, 'r', encoding='utf-8') as f:
            toc_data = json.load(f)
    else:

        files = {
            'input': args.input_file,
            'output': output_file,
            'output_dir': output_dir_path,
        
        }

        config = {
            'outline_blocks': args.outline_blocks,
            'outline_images': args.outline_images_tables,
            'outline_tables': args.outline_images_tables,
            'output_dir_path': output_dir_path,
            'header_size': args.header_size,
            'footer_size': args.footer_size,
            'include_pages': args.main_pages,
            'exclude_pages': args.exclude_pages,
            'toc_pages':  args.toc_pages,
        }

        # pages_data, filtered_pages_data, toc_data, images, tables, location_info = preprocess_pdf(files, config)
        result = preprocess_pdf(files, config)
        filtered_pages_data = result['filtered_pages_data']
        toc_data = result['toc_data']

        if not args.nofiles:
            json_output_file = os.path.join(output_dir_path, f"{os.path.basename(args.input_file)[:-4]}_blocks.json")
            with open(json_output_file, 'w', encoding='utf-8') as f:
                json.dump(result['pages_data'], f, ensure_ascii=False, indent=4)

            filtered_json_output_file = os.path.join(output_dir_path, f"filtered_{os.path.basename(args.input_file)[:-4]}_blocks.json")
            with open(filtered_json_output_file, 'w', encoding='utf-8') as f:
                json.dump(filtered_pages_data, f, ensure_ascii=False, indent=4)

            toc_json_output_file = os.path.join(output_dir_path, f"toc_{os.path.basename(args.input_file)[:-4]}_blocks.json")
            with open(toc_json_output_file, 'w', encoding='utf-8') as f:
                json.dump(toc_data, f, ensure_ascii=False, indent=4)

            with open(os.path.join(output_dir_path, "images.json"), "w", encoding="utf-8") as f:
                json.dump(result['images'], f, ensure_ascii=False, indent=4)

            with open(os.path.join(output_dir_path, "tables.json"), "w", encoding="utf-8") as f:
                json.dump(result['tables'], f, ensure_ascii=False, indent=4)

            with open(os.path.join(output_dir_path, "locations.json"), "w", encoding="utf-8") as f:
                json.dump(result['location_info'], f, ensure_ascii=False, indent=4)

    toc_regex_string = build_regex(toc_parsing_config)
    # print("TOC Regex: ", toc_regex_string)
    toc_regex_pattern = re.compile(toc_regex_string)

    toc_file_path = os.path.join(output_dir_path, "table_of_contents.json")
    _ = process_toc(toc_data, toc_file_path, toc_parsing_config, toc_regex_pattern)

    section_text_dir = os.path.join(output_dir_path, "section_text")
    os.makedirs(section_text_dir, exist_ok=True)

    analysis_config = global_config.get('analysis_config', {})
    sections = analyze_pdf(filtered_pages_data, analysis_config, section_text_dir)

    if not args.nofiles:
        sections_output_file = os.path.join(output_dir_path, f"{os.path.basename(args.input_file)[:-4]}_sections.json")
        with open(sections_output_file, 'w', encoding='utf-8') as f:
            json.dump(sections, f, ensure_ascii=False, indent=4)


if __name__ == "__main__":
    main()
