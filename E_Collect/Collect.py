from typing import List, Dict


def get_values_and_page_numbers(search_result_list: List[Dict], keyword_dict_of_lists: Dict[str, List[str]],
                                table_keywords: list, search_result_dict_key_name: str):
    results = dict()
    for key in keyword_dict_of_lists.keys():
        short_text_and_number_values = list()
        short_text_and_number_pages = list()
        for dictionary in search_result_list:
            if key in dictionary:
                value = dictionary[key][search_result_dict_key_name]
                page = dictionary['page_number']
                if len(value) > 0:
                    short_text_and_number_values.extend(value)
                    short_text_and_number_pages.append(page)
        results[key] = dict()
        results[key]['values'] = extract_number_from_short_text_set(list_of_strings=short_text_and_number_values,
                                                                    keyword_dict_of_lists=keyword_dict_of_lists,
                                                                    table_keywords=table_keywords)
        results[key]['pages'] = short_text_and_number_pages
    return results


def extract_number_from_short_text_set(list_of_strings: list, keyword_dict_of_lists: Dict[str, List[str]],
                                       table_keywords: list) -> list:
    text = make_string_from_list_of_strings(list_of_strings=list_of_strings)
    keywords = [keyword for keyword_list in keyword_dict_of_lists.values() for keyword in keyword_list]
    keywords.extend(table_keywords)
    keywords_sorted = sorted(keywords, key=len, reverse=True)
    numbers_in_sentence = [word.replace(',', '').replace('.', '') for word in text.split() if
                           word not in keywords_sorted and word.replace(',', '').replace('.', '').isdigit() and
                           len(word) > 1]
    return numbers_in_sentence


def make_string_from_list_of_strings(list_of_strings: list):
    concat_string = ""
    for item in list_of_strings:
        concat_string = concat_string + ' ' + item
    return concat_string
