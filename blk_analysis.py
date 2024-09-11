import argparse
import os
import yaml
import pymupdf
import json
from blocks.pdf_processor import preprocess_pdf, analyze_pdf
from blocks.toc_parser import process_toc


def parse_arguments():
    """
    Parse command line arguments
    """
    parser = argparse.ArgumentParser(description='Process PDF to outline blocks and extract text details')
    parser.add_argument('input_file', help='Input PDF file')
    parser.add_argument('-o', '--output_file', help='Output PDF file')
    parser.add_argument('--outline_blocks', action='store_true', help='Outline blocks in the PDF')
    parser.add_argument('-ad', '--appdir', help='Application directory', default='pdf_blocks')
    parser.add_argument('-od', '--output_dir', help='Output directory')
    parser.add_argument('-hs', '--header_size', type=float, default=0.07, help='Header size as a percentage of the page height (e.g., 0.1 for 10%%)')
    parser.add_argument('-fs', '--footer_size', type=float, default=0.07, help='Footer size as a percentage of the page height (e.g., 0.1 for 10%%)')
    parser.add_argument('-main', '--main_pages', help='List of page ranges for the main document (e.g., "1-3,5,7-")')
    parser.add_argument('-exclude', '--exclude_pages', help='List of page ranges to exclude (e.g., "4,6,8-10")')
    parser.add_argument('-toc', '--toc_pages', help='List of page ranges for the table of contents (e.g., "2-3")')
    parser.add_argument('-cfg','--config_file', help='Path to the YAML configuration file')
    parser.add_argument('-skip','--skip_preprocessing', action='store_true', help='Skip the preprocessing phase and use the filtered data input file')
    parser.add_argument('--filtered_data_file', help='Path to the filtered data input file')
    parser.add_argument('-tcfg','--toc_parsing_config', help='TOC parsing configuration to use from the global config file')
    parser.add_argument('-scfg','--section_parsing_config', help='Section parsing configuration to use from the global config file')
    return parser.parse_args()


def load_global_config(config_file):
    if os.path.exists(config_file):
        with open(config_file, 'r') as f:
            return yaml.safe_load(f)
    return {}


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

    toc_parsing_config = global_config.get('toc_parsing_configurations', {}).get(args.toc_parsing_config or 'default', {})
    section_parsing_config = global_config.get('section_parsing_configurations', {}).get(args.section_parsing_config or 'default', {})

    output_dir = args.output_dir if args.output_dir else os.path.basename(args.input_file)[:-4]
    app_dir = args.appdir
    output_dir_path = os.path.join(app_dir, output_dir)
    os.makedirs(output_dir_path, exist_ok=True)

    output_file = args.output_file if args.output_file else os.path.join(output_dir_path, f"{os.path.basename(args.input_file)[:-4]}_blocks.pdf")

    if args.skip_preprocessing:
        filtered_data_file = args.filtered_data_file if args.filtered_data_file else os.path.join(output_dir_path, f"filtered_{os.path.basename(args.input_file)[:-4]}_blocks.json")
        toc_data_file = os.path.join(output_dir_path, f"toc_{os.path.basename(args.input_file)[:-4]}_blocks.json")
        
        with open(filtered_data_file, 'r', encoding='utf-8') as f:
            filtered_pages_data = json.load(f)
        
        with open(toc_data_file, 'r', encoding='utf-8') as f:
            toc_data = json.load(f)
    else:
        doc = pymupdf.open(args.input_file)

        pages_data, filtered_pages_data, toc_data, images, tables, location_info = preprocess_pdf(
            doc, args.input_file, output_file, args.outline_blocks, app_dir, output_dir_path,
            args.header_size, args.footer_size, args.main_pages, args.exclude_pages, args.toc_pages
        )

        json_output_file = os.path.join(output_dir_path, f"{os.path.basename(args.input_file)[:-4]}_blocks.json")
        with open(json_output_file, 'w', encoding='utf-8') as f:
            json.dump(pages_data, f, ensure_ascii=False, indent=4)

        filtered_json_output_file = os.path.join(output_dir_path, f"filtered_{os.path.basename(args.input_file)[:-4]}_blocks.json")
        with open(filtered_json_output_file, 'w', encoding='utf-8') as f:
            json.dump(filtered_pages_data, f, ensure_ascii=False, indent=4)

        toc_json_output_file = os.path.join(output_dir_path, f"toc_{os.path.basename(args.input_file)[:-4]}_blocks.json")
        with open(toc_json_output_file, 'w', encoding='utf-8') as f:
            json.dump(toc_data, f, ensure_ascii=False, indent=4)

        with open(os.path.join(output_dir_path, "images.json"), "w", encoding="utf-8") as f:
            json.dump(images, f, ensure_ascii=False, indent=4)

        with open(os.path.join(output_dir_path, "tables.json"), "w", encoding="utf-8") as f:
            json.dump(tables, f, ensure_ascii=False, indent=4)

        with open(os.path.join(output_dir_path, "locations.json"), "w", encoding="utf-8") as f:
            json.dump(location_info, f, ensure_ascii=False, indent=4)

    toc_file_path = os.path.join(output_dir_path, "table_of_contents.json")
    toc_entries = process_toc(toc_data, toc_file_path, toc_parsing_config)

    sections = analyze_pdf(filtered_pages_data, section_parsing_config)

    sections_output_file = os.path.join(output_dir_path, f"{os.path.basename(args.input_file)[:-4]}_sections.json")
    with open(sections_output_file, 'w', encoding='utf-8') as f:
        json.dump(sections, f, ensure_ascii=False, indent=4)


if __name__ == "__main__":
    main()
