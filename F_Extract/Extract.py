import pandas as pd


def get_most_common_values(values: list or set, num_of_return_values: int) -> list or set:
    return sorted(values, key=values.count, reverse=True)[:num_of_return_values]


def aggregate_results(text_numbers_and_pages: dict, table_numbers_and_pages: dict,
                      num_of_return_values: int = 3) -> dict:
    if text_numbers_and_pages.keys() != table_numbers_and_pages.keys():
        raise KeyError('text_numbers_and_pages and table_numbers_and_pages have different keys !')
    all_pages = list()
    result_dict = dict()
    for scope in text_numbers_and_pages.keys():
        number_list = text_numbers_and_pages[scope]['values'] + table_numbers_and_pages[scope]['values']
        number_list_sorted_and_sized = get_most_common_values(values=number_list,
                                                              num_of_return_values=num_of_return_values)
        result_dict[scope] = number_list_sorted_and_sized
        page_list = text_numbers_and_pages[scope]['pages'] + table_numbers_and_pages[scope]['pages']
        all_pages.append(page_list) if page_list is not None else None
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
