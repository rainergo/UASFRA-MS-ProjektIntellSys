import os
import re
import pandas as pd
from collections import Counter
from operator import itemgetter
from typing import Set, List, Tuple

from A_Configuration_and_Logs.conf_and_log import ConfLog
from D_Search.PDFMinerNEW import PDFMiner
# from D_Search.HelperFunctions import get_first_last_indices_of_keyword_in_string
from E_Collect.Collect import get_values_and_page_numbers


# def get_most_common_values(values: list or set, num_of_return_values: int) -> list or set:
#     return sorted(values, key=values.count, reverse=True)[:num_of_return_values]


def get_most_common_values(values: list or set, num_of_return_values: int) -> list:
    return [word for word, word_count in Counter(values).most_common(num_of_return_values)]


def concat_strings_in_set(my_set_of_strings: Set[str]) -> str:
    text = ''
    for sentence in my_set_of_strings:
        text += sentence
    return text


def instantiate_unit_dict_from_list(my_list: List[str]) -> dict:
    dictionary = dict()
    for list_item in my_list:
        dictionary[list_item] = 0
    return dictionary


def sort_dictionary_by_key_len(dictionary: dict):
    sorted_dictionary = {}
    for k in sorted(dictionary, key=len, reverse=True):
        sorted_dictionary[k] = dictionary[k]
    return sorted_dictionary


def unit_counter(set_of_strings: Set[str], unit_list: List[str]) -> dict:
    sentence = concat_strings_in_set(my_set_of_strings=set_of_strings)
    unit_dict = instantiate_unit_dict_from_list(unit_list)
    sorted_dict = sort_dictionary_by_key_len(unit_dict)
    for key in sorted_dict.keys():
        matches = re.finditer(key, sentence)
        for match in matches:
            sentence = sentence.replace(match.group(),'')
            unit_dict[key] += 1
    return unit_dict


def get_most_likely_unit(set_of_strings: Set[str], unit_list: List[str]):
    unit_dict = unit_counter(set_of_strings=set_of_strings, unit_list=unit_list)
    return max(unit_dict.items(), key=itemgetter(1))[0]


def aggregate_results(neighbour_numbers_and_pages: dict, table_numbers_and_pages: dict, text_numbers_and_pages: dict,
                      num_of_return_values: int = 3) -> dict:
    if neighbour_numbers_and_pages.keys() != table_numbers_and_pages.keys() != text_numbers_and_pages.keys():
        raise KeyError('neighbour_numbers_and_pages and table_numbers_and_pages have different keys !')
    all_pages = list()
    result_dict = dict()
    for scope in neighbour_numbers_and_pages.keys():
        number_list = neighbour_numbers_and_pages[scope]['values'] + table_numbers_and_pages[scope]['values'] + \
                      text_numbers_and_pages[scope]['values']
        number_list_sorted_and_sized = get_most_common_values(values=number_list,
                                                              num_of_return_values=num_of_return_values)
        result_dict[scope] = number_list_sorted_and_sized
        page_list = neighbour_numbers_and_pages[scope]['pages'] + table_numbers_and_pages[scope]['pages']
        unique_page_list = list(set(page_list))
        all_pages.append(unique_page_list) if page_list is not None else None
    result_dict['AbsSeiten'] = all_pages
    return result_dict


def add_descriptive_data(number_and_pages_dict: dict, year: str, name_of_pdf: str, weight_unit: str = 'Tonnen',
                         first_name: str = 'Rainer') -> dict:
    result_dict = {'Vorname': first_name}
    result_dict.update(number_and_pages_dict)
    result_dict['Jahr'] = year
    result_dict['Gewichtseinheit'] = weight_unit
    result_dict['NamePDF'] = name_of_pdf
    return result_dict


def create_result_dataframe(result_dict: dict, result_dataframe: pd.DataFrame = None) -> pd.DataFrame:
    if result_dataframe is None or result_dataframe.empty:
        result_dataframe = pd.DataFrame([result_dict])
    else:
        result_dataframe = result_dataframe.append(result_dict, ignore_index=True)
    return result_dataframe


def analyze_pdfs() -> pd.DataFrame:
    conf_log = ConfLog()
    df_aggregate = None
    for pdf_doc in os.scandir(conf_log.path_to_reports_for_analysis_directory):
        filename = os.fsdecode(pdf_doc)
        if filename.endswith(".pdf"):
            try:
                miner = PDFMiner(path=filename)
                table_keywords = miner.get_year_and_fy()
                # print('table_keywords:', table_keywords)
                search_result = miner.find_word(keywords_dict_of_list=conf_log.keyword_dict_of_lists,
                                                search_word_list=conf_log.search_word_list,
                                                table_keywords=table_keywords,
                                                neighbour_x_tolerance=conf_log.find_word_neighbour_x_tolerance,
                                                neighbour_y_tolerance=conf_log.find_word_neighbour_y_tolerance,
                                                table_x_tolerance=conf_log.find_word_table_x_tolerance,
                                                table_y_tolerance=conf_log.find_word_table_y_tolerance,
                                                decimals=conf_log.find_word_decimals)
                # print('Search Results:\n', search_result)
                """ The matching sentences (for potential word2vec) are stored in miner.matching_sentences """
                # print('miner.matching_sentences:', miner.matching_sentences)
                most_likely_unit = get_most_likely_unit(set_of_strings=miner.matching_sentences, unit_list=conf_log.find_word_unit_list)
                # print('most_likely_unit:', most_likely_unit)
                table_numbers_and_pages = get_values_and_page_numbers(search_result_list=search_result,
                                                                      keyword_dict_of_lists=conf_log.keyword_dict_of_lists,
                                                                      num_of_return_values=conf_log.extract_number_of_table_vals_to_include,
                                                                      search_result_dict_key_name='table_values')
                #print('table_numbers_and_pages:', table_numbers_and_pages)
                neighbour_numbers_and_pages = get_values_and_page_numbers(search_result_list=search_result,
                                                                          keyword_dict_of_lists=conf_log.keyword_dict_of_lists,
                                                                          num_of_return_values=conf_log.extract_number_of_neighbour_vals_to_include,
                                                                          search_result_dict_key_name='neighbour_values')
                #print('neighbour_numbers_and_pages:', neighbour_numbers_and_pages)
                text_numbers_and_pages = get_values_and_page_numbers(search_result_list=search_result,
                                                                     keyword_dict_of_lists=conf_log.keyword_dict_of_lists,
                                                                     num_of_return_values=conf_log.extract_number_of_text_vals_to_include,
                                                                     search_result_dict_key_name='text_values')
                #print('text_numbers_and_pages:', text_numbers_and_pages)
                number_and_pages_dict = aggregate_results(neighbour_numbers_and_pages=neighbour_numbers_and_pages,
                                                          table_numbers_and_pages=table_numbers_and_pages,
                                                          text_numbers_and_pages=text_numbers_and_pages,
                                                          num_of_return_values=conf_log.extract_number_of_vals_to_include)

                result_dict = add_descriptive_data(number_and_pages_dict=number_and_pages_dict, year=table_keywords[0],
                                                   name_of_pdf=str(pdf_doc.name), weight_unit=most_likely_unit)

                df_aggregate = create_result_dataframe(result_dict=result_dict, result_dataframe=df_aggregate)
                miner.stream.close()
            except Exception as e:
                conf_log.logging.error(e, exc_info=True)
    return df_aggregate
