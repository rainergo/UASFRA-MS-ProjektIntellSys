import re
from typing import List, Tuple


def get_places_of_keyword_in_string(sentence: str, keyword: str) -> list:
    """ This function will NOT return the index of the first word character in the sentence,
    but the x-th place(s) of a WORD in a sentence of words that are seperated by white spaces """
    all_places_of_keyword_in_sentence = list()
    for place_of_keyword_in_sentence, word in enumerate(sentence.split()):
        if word.lower() == keyword.lower():
            all_places_of_keyword_in_sentence.append(place_of_keyword_in_sentence)
    return all_places_of_keyword_in_sentence


def get_first_last_indices_of_keyword_in_string(sentence: str, keyword: str) -> List[Tuple]:
    start_end_index_set = set()
    for word in re.finditer(keyword, sentence):
        start_index = word.start()
        end_index = word.end()
        start_end_index_set.add((start_index, end_index))
    return list(start_end_index_set)
