from typing import List, Dict
from collections import Counter


def get_most_common_values_2(values: list or set, num_of_return_values: int) -> list:
    return [word for word, word_count in Counter(values).most_common(num_of_return_values)]


def get_values_and_page_numbers(search_result_list: List[Dict], keyword_dict_of_lists: Dict[str, List[str]],
                                num_of_return_values: int, search_result_dict_key_name: str):
    results = dict()
    for key in keyword_dict_of_lists.keys():
        values = list()
        pages = list()
        for dictionary in search_result_list:
            if key in dictionary:
                value = dictionary[key][search_result_dict_key_name]
                page = dictionary['page_number']
                if len(value) > 0:
                    values.extend(value)
                    pages.append(page)
        values = get_most_common_values_2(values=values, num_of_return_values=num_of_return_values)
        results[key] = dict()
        results[key]['values'] = values
        results[key]['pages'] = pages
    return results


def extract_number_from_short_text_set(list_of_strings: list, keyword_dict_of_lists: Dict[str, List[str]],
                                       table_keywords: list) -> list:
    text = make_string_from_list_of_strings(list_of_strings=list_of_strings)
    keywords = [keyword for keyword_list in keyword_dict_of_lists.values() for keyword in keyword_list]
    keywords.extend(table_keywords)
    keywords_sorted = sorted(keywords, key=len, reverse=True)
    numbers_in_sentence = [word for word in text.split() if
                           word not in keywords_sorted and word.replace(',', '').replace('.', '').isdigit() and
                           len(word) > 1]
    return numbers_in_sentence


def make_string_from_list_of_strings(list_of_strings: list):
    concat_string = ""
    for item in list_of_strings:
        concat_string = concat_string + ' ' + item
    return concat_string
