import re
import os
from functools import partial

# section_number = None
# section_text = ""
# number_parsing = ""
# division_parsing = []
# 
# increment_functions = {
#     'numeric':  increment_numeric
# }
# 
# division info:
#     number_parsing to use
#     number validation to use
#     list of division parsing to look for
# 
# 
# for all text segments:
#     analyze text segments
# 
# Finish last segment
# 
# def analyze_text_semgent(text):
# 
#     # check if text matches division
#     # if so:
#     #   get division type
#     #   set current number
#     #   end previous section/text
#     #   end the division (if needed)
#     #   change number parsing
#     #   change divisition parsing`
#     #  continue parsing

from pprint import pprint


def increment_numeric(value):
    return str(int(value) + 1)

increment_functions = {
        'numeric': increment_numeric,
}


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

        # self.division_config = dtypes[division_type]
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


class SegmentAnalyzer():

    def __init__(self, config, text_dir, division_type='default'):
        self.section_id = 0
        self.text_dir = text_dir
        self.config = config
        self.section_number = None
        self.section_prefix = None
        self.section_text = ""
        self.set_division(division_type)
        self.last_div_search_config = None
        self.section_record = None
        self.section_list = []

    def set_division(self, division_type):
        dtypes = self.config.get('division_types', {})

        if division_type not in dtypes:
            print(f"Division type {division_type} is not defined in the configuration file")
            return

        self.division_config = dtypes[division_type]

    def get_section_list(self):
        return self.section_list

    def is_valid_next_section_number(self, separator, next_section=None):

        # TODO -- don't add separator if ""
        def add_prefix(s, separator):
            # if both a prefix and non empty string, return both with a separator
            if self.section_prefix and s != "":
                return self.section_prefix + separator + s
            # otherwise if there isn't a prefix, just return s
            elif not self.section_prefix:
                return s
            # other s must be empty, so return prefix
            else:
                return self.section_prefix

        numbering_model_name = self.division_config['numbering_rules']
        numbering_model = self.config['numbering_rules'][numbering_model_name]['sequence_rules']
#        print("Numbering Model:")
#        pprint(numbering_model)

        # if no previous section, the first section must be one of the
        # following
        if self.section_number is None:
            # build the valid number list adding the prefix if there is one
            # TODO check if prefix?
            add_prefix_with_sep = partial(add_prefix, separator=separator)
            valid_numbers = map(add_prefix_with_sep, numbering_model['initial_section_number'])
            if next_section in valid_numbers:
                return True

            return False

        parts = self.section_number.split(separator)

        # check the next section against all of the possible sub-sections
        # based on the list of what digits can a new set of subsections start with
        for next_num in numbering_model['level_starts']:
            # since we're looping through multiple options,
            # reset our 'prev_section_parts back to parts for each loop/option
            prev_section_parts = parts
            prev_section_parts.append(str(next_num))
            next_valid_section = separator.join(prev_section_parts)

            if next_section == next_valid_section:
                # print(f"SA: Valid {next_valid_section} {next_section}")
                return True

        # prev_section_parts will have one (and only one) additional sublevel from above
        # (which will be promptly rempved in the while lop below as
        # the code checks for a possible match at leave sub-level

        # if there is a prefix, remove it from string we check (as it won't be in the prev section either)
        if self.section_prefix:
            next_section = separator.join(next_section.split(separator)[1:])
            prev_section_parts = prev_section_parts[1:]

        while prev_section_parts := prev_section_parts[:-1]:
            # print(f"Checking {prev_section_parts}")
            increment_func = increment_functions[numbering_model['increment']]
            prev_section_parts[-1] = increment_func(prev_section_parts[-1])
            next_valid_section = separator.join(prev_section_parts)

            if next_section== next_valid_section:
                # print(f"SA: Valid {next_valid_section}")
                return True

            # for the first level, also allow X.<level start options>
            if len(prev_section_parts) == 1:
                for next_num in numbering_model['level_starts']:
                    next_check = next_valid_section + separator + str(next_num)

                    if next_section == next_check:
                        # print(f"SA: Valid {next_valid_section}")
                        return True

        return False

    def analyze_segment(self, text, page_number, debug=False):
        # check for start of new divisions
        for dtype in self.division_config['division_search_rules']:
            dtype_config = self.config['division_search_rules'][dtype]
            div_search_config = dtype_config['regex']
            if self.last_div_search_config != div_search_config:
                print(f"New search config {div_search_config}")
            self.last_div_search_config = div_search_config
            div_regex = re.compile(div_search_config)
            div_match = div_regex.match(text)
            if debug:
                print(f"ANALYZE SEG: Checking {text} with rule {div_search_config}")

            if div_match:
                self.set_division(dtype)
                number_field = dtype_config.get('number_match', None)
                prefix_field = dtype_config.get('prefix_match', None)
                if number_field is not None:
                    self.section_number = div_match.group(number_field)
                    print(f"New Div: Setting number to  {self.section_number}")
                else:
                    self.section_number = None

                if prefix_field is not None:
                    self.section_prefix = div_match.group(prefix_field)
                    print(f"New Div: Setting prefix to  {self.section_prefix}")
                else:
                    self.section_prefix = None

                print(f"Segment Analyzer:  Found div type {dtype} number: {self.section_number or 'NA'} pref: {self.section_prefix or 'NA'} (text: {text}")
                # TODO -- close previous section
                self.section_text = ""
                return

        numb_rule_name = self.division_config['numbering_rules']
        if numb_rule_name is not None:
            numbering = self.config['numbering_rules'][numb_rule_name]
            parsing_config = self.config['parsing_rules']['common']
            parsing_rule_name = numbering['parsing_rules']
            parsing_config = parsing_config | self.config['parsing_rules'][parsing_rule_name]
            numbering_regex_string = build_regex(parsing_config)
            numbering_regex_pattern = re.compile(numbering_regex_string)
            numbering_match = numbering_regex_pattern.match(text)
            if numbering_match:
                next_section_number = numbering_match.group('number')
                separator = "."  # TODO configure this
                # print(f"Checking {next_section_number} {text}")
                if self.is_valid_next_section_number(separator, next_section_number):
                    # TODO -- close previous section
                    print(f"SA - Valid New Section {next_section_number}")
                    if self.section_record:
                        section_text_file = os.path.join(self.text_dir, self.section_record['textfile'])
                        with open(section_text_file, "w") as output:
                            output.write(self.section_text)

                        self.section_list.append(self.section_record)
                        pprint(self.section_record)

                    self.section_number = next_section_number
                    self.section_text = ""
                    # since we found the line that has the title, there will not be text yet
                    # so start the section with empty text
                    self.section_record = {
                        "id":  self.section_id,
                        "start_page": page_number,
                        "textfile":  f"section_{self.section_id}.txt"
                    }
                    self.section_id += 1

                    # add in all the sections from the regex groups matches
                    for group in parsing_config['regex_groups']:
                        if isinstance(parsing_config[group], dict):
                            self.section_record[group] = numbering_match.group(group)
                        else:
                            self.section_record[group] = numbering_match.group(group)
                    return

            self.section_text += text + "\n"
