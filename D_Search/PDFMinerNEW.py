from io import StringIO
from pdfminer.layout import LAParams, LTTextBox, LTTextContainer, LTTextLine, LTTextLineHorizontal, LTChar
from pdfminer.pdfdevice import PDFDevice
from pdfminer.pdfpage import PDFPage, PDFTextExtractionNotAllowed
from pdfminer.pdfinterp import PDFResourceManager
from pdfminer.pdfinterp import PDFPageInterpreter
from pdfminer.converter import PDFPageAggregator, PDFConverter
from pdfminer.converter import TextConverter
from pdfminer.pdfdocument import PDFDocument
from pdfminer.pdftypes import resolve1
from pdfminer.pdfparser import PDFParser
from pdfminer.psparser import PSLiteral, PSKeyword
from pdfminer.utils import decode_text
from pdfminer.high_level import extract_pages
from typing import List, Dict, Set, Tuple
import re
import math
from itertools import islice
# from HelperFunctions import get_first_last_indices_of_keyword_in_string
from A_Configuration_and_Logs.conf_and_log import ConfLog

""" Documentation is here:
    https://pdfminersix.readthedocs.io/en/latest/index.html
"""


class XYWordMatch:
    """Class for keeping track of (coordinates for) Text objects that match the search word."""

    def __init__(self, x0: float, x1: float, y0: float, y1: float, neighbour_x_tolerance: float = 0.75,
                 neighbour_y_tolerance: float = 0.75, table_x_tolerance: float = 0.75, table_y_tolerance: float = 0.75):
        self.neighbour_x_tolerance = neighbour_x_tolerance
        self.neighbour_y_tolerance = neighbour_y_tolerance
        """ See comment in set_table_keyword_value_coordinates_plus_tolerance-method: """
        self.table_x_tolerance = table_x_tolerance
        self.table_y_tolerance = table_y_tolerance
        self.x_coordinates_plus_neighbour_tolerance = list()
        self.y_coordinates_plus_neighbour_tolerance = list()
        self.xx_coordinates_table_keyword_values_plus_tolerance = list()
        self.yy_coordinates_table_keyword_values_plus_tolerance = list()
        self.x_coordinates = (x0, x1)
        self.y_coordinates = (y0, y1)
        self.neighbour_values = list()
        self.text_values = list()
        self.table_values = list()

    @property
    def x_coordinates(self) -> tuple:
        return self._x_coordinates

    @x_coordinates.setter
    def x_coordinates(self, value: tuple):
        x0, x1 = value
        self._x_coordinates = (x0, x1)
        self.x_coordinates_plus_neighbour_tolerance.append(self._calc_x_neighbour_tolerance(x0=x0, x1=x1))

    @property
    def y_coordinates(self) -> tuple:
        return self._y_coordinates

    @y_coordinates.setter
    def y_coordinates(self, value: tuple):
        y0, y1 = value
        self._y_coordinates = (y0, y1)
        self.y_coordinates_plus_neighbour_tolerance.append(self._calc_y_neighbour_tolerance(y0=y0, y1=y1))
        self.set_table_keyword_value_y_coordinates_plus_tolerance(y0=y0, y1=y1)

    def xx0_xx1_is_within_neighbour_bounds(self, xx0: float, xx1: float) -> bool:
        return len(([(x_tol[0], x_tol[1]) for x_tol in self.x_coordinates_plus_neighbour_tolerance if
                     (xx0 >= x_tol[0] and xx1 <= x_tol[1])])) > 0

    def yy0_yy1_is_within_neighbour_bounds(self, yy0: float, yy1: float) -> bool:
        return len(([(y_tol[0], y_tol[1]) for y_tol in self.y_coordinates_plus_neighbour_tolerance if
                     (yy0 >= y_tol[0] and yy1 <= y_tol[1])])) > 0

    def add_neighbour_values(self, text: str):
        self.neighbour_values.append(text)

    def add_text_values(self, text: str):
        self.text_values.append(text)

    def add_table_values(self, text: str):
        self.table_values.append(text)

    def _calc_y_neighbour_tolerance(self, y0: float, y1: float) -> tuple:
        y_tolerance = (y1 - y0) * self.neighbour_y_tolerance
        y0_lower = y0 - y_tolerance
        y1_upper = y1 + y_tolerance
        return y0_lower, y1_upper

    def _calc_x_neighbour_tolerance(self, x0: float, x1: float) -> tuple:
        x_tolerance = (x1 - x0) * self.neighbour_x_tolerance
        x0_lower = x0 - x_tolerance
        x1_upper = x1 + x_tolerance
        return x0_lower, x1_upper

    def set_table_keyword_value_x_coordinates_plus_tolerance(self, x0: float, x1: float):
        """ The y-position should only be minimally different from the keyword position, but the x-position could
        deviate more from the table_keyword-position due to different size of table_keyword and the keyword value """
        x_tolerance = (x1 - x0) * self.table_x_tolerance
        x0_lower = x0 - x_tolerance
        x1_upper = x1 + x_tolerance
        self.xx_coordinates_table_keyword_values_plus_tolerance.append((x0_lower, x1_upper))

    def set_table_keyword_value_y_coordinates_plus_tolerance(self, y0: float, y1: float):
        """ The y-position should only be minimally different from the keyword position, but the x-position could
        deviate more from the table_keyword-position due to different size of table_keyword and the keyword value """
        y_tolerance = (y1 - y0) * self.table_y_tolerance
        y0_lower = y0 - y_tolerance
        y1_upper = y1 + y_tolerance
        self.yy_coordinates_table_keyword_values_plus_tolerance.append((y0_lower, y1_upper))

    def are_table_keyword_x_coordinates_within_tolerance(self, xx0: float, xx1: float) -> bool:
        x_within_bounds = len(
            ([(x_tol[0], x_tol[1]) for x_tol in self.xx_coordinates_table_keyword_values_plus_tolerance if
              (xx0 >= x_tol[0] and xx1 <= x_tol[1])])) > 0
        return x_within_bounds

    def are_table_keyword_y_coordinates_within_tolerance(self, yy0: float, yy1: float) -> bool:
        y_within_bounds = len(
            ([(y_tol[0], y_tol[1]) for y_tol in self.yy_coordinates_table_keyword_values_plus_tolerance if
              (yy0 >= y_tol[0] and yy1 <= y_tol[1])])) > 0
        return y_within_bounds


class PDFMiner:

    def __init__(self, path: str):
        self.path = path
        self.conf_log = ConfLog()
        self.stream = open(path, 'rb')
        self.parser = PDFParser(self.stream)
        self.document = PDFDocument(self.parser)
        self.doc_is_extractable = self.document.is_extractable
        self.resource_manager = PDFResourceManager()
        """ 
        My standard settings for layout parameters:
        (line_overlap=0.5, char_margin=2.0, line_margin=0.75, word_margin=0.1, boxes_flow=0.0,
                                                        detect_vertical=False, all_texts=True)
        Default settings for layout parameters:
        (line_overlap=0.5, char_margin=2.0, line_margin=0.5, word_margin=0.1,boxes_flow=0.5, detect_vertical=False, 
        all_texts=False)
        Source: https://pdfminersix.readthedocs.io/en/latest/reference/composable.html#laparams """
        self.layout_params = LAParams(line_overlap=self.conf_log.pdfminer_layout_line_overlap,
                                      char_margin=self.conf_log.pdfminer_layout_char_margin,
                                      line_margin=self.conf_log.pdfminer_layout_line_margin,
                                      word_margin=self.conf_log.pdfminer_layout_word_margin,
                                      boxes_flow=self.conf_log.pdfminer_layout_boxes_flow,
                                      detect_vertical=self.conf_log.pdfminer_layout_detect_vertical,
                                      all_texts=self.conf_log.pdfminer_layout_all_texts)
        self.device = TextConverter(rsrcmgr=self.resource_manager, outfp=StringIO(), laparams=self.layout_params)
        self.page_aggregator = PDFPageAggregator(rsrcmgr=self.resource_manager, laparams=self.layout_params)
        self.interpreter = PDFPageInterpreter(self.resource_manager, self.device)
        self.pages = PDFPage.get_pages(fp=self.stream, pagenos=None, maxpages=0, password='',
                                       caching=True, check_extractable=False)
        self.pages = extract_pages(pdf_file=path, laparams=self.layout_params)

    def process_pages(self):
        page_number = 0
        for page in self.pages:
            page_number += 1
            print('Processing next page...')
            self.interpreter.process_page(page)
            layout = self.page_aggregator.get_result()
            for lobj in layout:
                if isinstance(lobj, LTTextContainer):
                    print('Type is:', type(lobj))
                    one, two, three, four, text = lobj.bbox[0], lobj.bbox[1], lobj.bbox[2], lobj.bbox[
                        3], lobj.get_text()
                    print(f'At {one}, {two}, {three}, {four} text is: {text}')

    def find_word(self, keywords_dict_of_list: Dict[str, List[str]], search_word_list: List[str],
                  neighbour_x_tolerance: float, neighbour_y_tolerance: float,
                  table_keywords: List[str], table_x_tolerance: float = 3.50, table_y_tolerance: float = 0.25,
                  table_value_max_len: int = 12, short_text_max_len: int = 50, decimals: int = 1):
        if not self.doc_is_extractable:
            raise PDFTextExtractionNotAllowed('The pdf document does not allow extraction ! ')
        findings = list()
        page_number = 0
        """ I. Iterate over all pages: """
        for all_layout_objects_on_one_page in self.pages:
            page_number += 1
            page_findings = dict()
            """ II. Iterate over all keyword_lists in the keyword_list_of_lists: """
            for keywords_key, keywords_list in keywords_dict_of_list.items():
                list_of_word_match_objects = list()
                set_of_table_keyword_coordinate_tuples = set()
                set_of_matching_sentences_in_text_container = set()
                """ III. Iterate over all LTTextContainer objects (called: text_container) on a page: """
                for text_container in all_layout_objects_on_one_page:
                    if isinstance(text_container, LTTextContainer) or isinstance(text_container, LTTextLine):
                        """ III.A. Get matching text of text container for word2vec analysis """
                        text_in_text_container = text_container.get_text()
                        clean_text_in_text_container = ' '.join(text_in_text_container.split())
                        """ Find sentences that contain both, any one keyword AND any one search_word """
                        matching_sentences_in_text_container = \
                            get_sentences_if_they_contain_words_of_two_search_lists(text_string=clean_text_in_text_container,
                                                                                  word_list_one=keywords_list,
                                                                                  word_list_two=search_word_list)
                        ########################################
                        # print('matching_sentences_in_text_container:', matching_sentences_in_text_container)
                        #########################################
                        for sentence in matching_sentences_in_text_container:
                            set_of_matching_sentences_in_text_container.add(sentence)

                        """ III.B. Get XY-Coordinates of keywords and table headings (table_keywords) ... """
                        for text_line in text_container:
                            """ Get xy-coordinates of keywords """
                            keyword_coordinates_in_text_line = self.get_coordinates_of_keyword(
                                text_line_object=text_line,
                                keywords_list=keywords_list)
                            if keyword_coordinates_in_text_line is not None:
                                for x0, y0, x1, y1 in keyword_coordinates_in_text_line:
                                    """ If keyword matches content of this Text object, then initiate the data carrier object
                                    (XYWordMatch-instance) and store position data there: """
                                    word_match = XYWordMatch(x0=x0, x1=x1, y0=y0, y1=y1,
                                                             neighbour_x_tolerance=neighbour_x_tolerance,
                                                             neighbour_y_tolerance=neighbour_y_tolerance,
                                                             table_x_tolerance=table_x_tolerance,
                                                             table_y_tolerance=table_y_tolerance)
                                    list_of_word_match_objects.append(word_match)
                            """ Get xy-coordinates of table_keywords """
                            table_keyword_coordinates_in_text_line = self.get_coordinates_of_keyword(
                                text_line_object=text_line,
                                keywords_list=table_keywords)
                            if table_keyword_coordinates_in_text_line is not None:
                                #######################
                                # print('set_of_table_keyword_coordinate_tuples:', set_of_table_keyword_coordinate_tuples)
                                #####################
                                set_of_table_keyword_coordinate_tuples.update(table_keyword_coordinates_in_text_line)

                """III.B. ... and set xy-coordinates for potential table_keyword-values (with these coordinates) 
                later """
                list_of_word_match_objects = self.set_x_coordinates_of_table_keyword_values(
                    set_of_table_keyword_coordinate_tuples=set_of_table_keyword_coordinate_tuples,
                    list_of_word_match_objects=list_of_word_match_objects,
                    decimals=decimals)

                """ IV. Get all the values """
                for text_container in all_layout_objects_on_one_page:
                    if isinstance(text_container, LTTextContainer):
                        for text_line in text_container:
                            if isinstance(text_line, LTTextLine):
                                """ IV.A. Get neighbour values """
                                list_of_word_match_objects = \
                                    self.get_neighbour_values(text_line_object=text_line,
                                                              list_of_word_match_objects=list_of_word_match_objects,
                                                              decimals=decimals)
                                """ IV.B. Get table values """
                                list_of_word_match_objects = \
                                    self.get_table_values(text_line_object=text_line,
                                                          list_of_word_match_objects=list_of_word_match_objects,
                                                          decimals=decimals)

                """ Collect all data for each keyword_list """
                if len(list_of_word_match_objects) > 0 or len(set_of_matching_sentences_in_text_container) > 0:
                    container_findings = dict()
                    container_findings['text_values'] = set()
                    container_findings['neighbour_values'] = set()
                    container_findings['table_values'] = set()
                    if len(set_of_matching_sentences_in_text_container) > 0:
                        for sentence in set_of_matching_sentences_in_text_container:
                            ###################################
                            numbers = self.text_filter(sentence=sentence)
                            for number in numbers:
                                if number is not None:
                                    container_findings['text_values'].add(number)
                            ##################################################################
                    for word_match_object in list_of_word_match_objects:
                        if len(word_match_object.neighbour_values) > 0:
                            for neighbour_value in word_match_object.neighbour_values:
                                val = self.neighbour_and_table_value_filter(value=neighbour_value)
                                if val is not None:
                                    container_findings['neighbour_values'].add(val)
                        if len(word_match_object.table_values) > 0:
                            for table_value in word_match_object.table_values:
                                val = self.neighbour_and_table_value_filter(value=table_value)
                                if val is not None:
                                    container_findings['table_values'].add(val)
                    page_findings['page_number'] = page_number
                    page_findings[keywords_key] = container_findings

            """ Finally, append all keyword_list findings to an aggregated list ("findings"):"""
            if page_findings:
                findings.append(page_findings)
        return findings

    def get_year_and_fy(self) -> list or None:
        standard_year = self.conf_log.find_word_standard_year_if_year_not_found
        """ First, try to get year from file name """
        match = re.match(self.conf_log.find_word_year_regex, self.path)
        if match:
            year = match.group(1)
            return [year, 'FY' + year[-2:], 'FY' + year]
        """ Second, try to get year from first page (title) """
        pages = extract_pages(self.path, page_numbers=[0], maxpages=1)
        for page in pages:
            for layout_obj in page:
                if isinstance(layout_obj, LTTextContainer) or isinstance(layout_obj, LTTextLine):
                    text = layout_obj.get_text()
                    year_list = text.split()
                    for year in year_list:
                        if len(year) == 4 and is_digit(year) and year.startswith('20'):
                            return [year, 'FY' + year[-2:], 'FY' + year]
        """ If all fails, take standard year defined in config.ini """
        return [standard_year, 'FY' + standard_year[-2:], 'FY' + standard_year]

    def get_coordinates_of_keyword(self, text_line_object: LTTextLine, keywords_list: list, decimals: int = 1) -> \
            Set[Tuple] or None:
        if isinstance(text_line_object, LTTextLine) and text_line_object is not None and keywords_list is not None:
            text_in_line = text_line_object.get_text()
            if any(word in text_in_line for word in keywords_list):
                keyword_coordinates_in_text_line = set()
                for keyword in keywords_list:
                    start_end_indices = get_first_last_indices_of_keyword_in_string(sentence=text_in_line,
                                                                                    keyword=keyword)
                    for start, end in start_end_indices:
                        (x0, y0, x1, y1, word) = self.get_coordinates_and_word(text_line_object=text_line_object,
                                                                               start=start, end=end, decimals=decimals)
                        if all((x0, y0, x1, y1)):
                            keyword_coordinates_in_text_line.add((x0, y0, x1, y1))
                return keyword_coordinates_in_text_line if len(keyword_coordinates_in_text_line) > 0 else None
            else:
                return None

    def get_coordinates_of_word_in_text_line(self, text_line_object: LTTextLine, decimals: int) -> Set[Tuple] or None:
        if isinstance(text_line_object, LTTextLine) and text_line_object is not None:
            text_in_line = text_line_object.get_text()
            word_coordinates_in_text_line = set()
            start_end_indices = get_first_last_indices_of_all_words_in_string(sentence=text_in_line)
            for start, end in start_end_indices:
                (x0, y0, x1, y1, word) = self.get_coordinates_and_word(text_line_object=text_line_object,
                                                                       start=start, end=end, decimals=decimals)
                if all((x0, y0, x1, y1, word)):
                    word_coordinates_in_text_line.add((x0, y0, x1, y1, word))
            return word_coordinates_in_text_line if len(word_coordinates_in_text_line) > 0 else None
        else:
            return None

    def get_coordinates_and_word(self, text_line_object: LTTextLine, start: int, end: int,
                                 decimals: int) -> tuple or None:
        word_start_and_end = list(islice(text_line_object, start, end))
        """ There are some issues with strange fond types in some pdf docs in which case None is returned """
        if word_start_and_end is not None and len(word_start_and_end) > 0 \
                and isinstance(word_start_and_end[0],LTChar) and isinstance(word_start_and_end[-1], LTChar):
            x0 = round(word_start_and_end[0].bbox[0], decimals)
            y0 = round(word_start_and_end[0].bbox[1], decimals)
            x1 = round(word_start_and_end[-1].bbox[2], decimals)
            y1 = round(word_start_and_end[-1].bbox[3], decimals)
            word = ''
            for char in word_start_and_end:
                word += char.get_text()
            return x0, y0, x1, y1, word
        else:
            return None, None, None, None, None

    def set_x_coordinates_of_table_keyword_values(self, set_of_table_keyword_coordinate_tuples: set,
                                                  list_of_word_match_objects: List[XYWordMatch],
                                                  decimals: int) -> List[XYWordMatch]:
        """ Now set x-coordinates for potential table_keyword-values (with these coordinates) later """
        for x0, _, x1, _ in set_of_table_keyword_coordinate_tuples:
            for word_match_in_list in list_of_word_match_objects:
                word_match_in_list.set_table_keyword_value_x_coordinates_plus_tolerance(x0=round(x0, decimals),
                                                                                        x1=round(x1, decimals))
        return list_of_word_match_objects

    def get_neighbour_values(self, text_line_object: LTTextLine, list_of_word_match_objects: List[XYWordMatch],
                             decimals: int) -> List[XYWordMatch]:
        word_coordinates_list = self.get_coordinates_of_word_in_text_line(
            text_line_object=text_line_object, decimals=decimals)
        ####################################################
        # print('word_coordinates_list:', word_coordinates_list)
        #####################################################
        if list_of_word_match_objects is not None:
            for word_match_in_list in list_of_word_match_objects:
                if word_coordinates_list is not None:
                    for x0, y0, x1, y1, word in word_coordinates_list:
                        ################################
                        # print('xx_coordinates_table_keyword_values_plus_tolerance:',
                        #       word_match_in_list.xx_coordinates_table_keyword_values_plus_tolerance)
                        # print('yy_coordinates_table_keyword_values_plus_tolerance:',
                        #       word_match_in_list.yy_coordinates_table_keyword_values_plus_tolerance)
                        # print('x_coordinates_plus_neighbour_tolerance:',
                        #       word_match_in_list.x_coordinates_plus_neighbour_tolerance)
                        # print('y_coordinates_plus_neighbour_tolerance:',
                        #       word_match_in_list.y_coordinates_plus_neighbour_tolerance)
                        # print('word', word)
                        # print('x0:', x0)
                        # print('x1:', x1)
                        # print('y0:', y0)
                        # print('y1:', y1)
                        # print('---------------------------------')
                        #####################################
                        # print('word', word)

                        if word_match_in_list.xx0_xx1_is_within_neighbour_bounds(xx0=x0, xx1=x1) and \
                                word_match_in_list.yy0_yy1_is_within_neighbour_bounds(yy0=y0, yy1=y1):
                            # print('neighbour word:', word)
                            word_match_in_list.add_neighbour_values(word)
        #########################
        # for wm in list_of_word_match_objects:
        #     print('neighbour_values:', wm.neighbour_values)
        #############################
        return list_of_word_match_objects

    def neighbour_and_table_value_filter(self, value: str, thousands_separator: str = ',') -> float or None:
        clean_value = value.replace(thousands_separator, '')
        """ Exclude 'year' values such as 2020 or 2050. Con: If values look like years, they will be excluded """
        match = re.match(self.conf_log.find_word_year_regex, clean_value)
        if is_digit(clean_value) and not match and not single_digit_num_is_point_zero(clean_value) and \
                num_of_int_digits(word=clean_value) >= self.conf_log.find_word_min_num_int_digits_in_searched_value:
            return float(clean_value)
        else:
            return None

    def text_filter(self, sentence: str, separator: str = ' ', thousands_separator: str = ',') -> List[float]:
        numbers = list()
        for word in sentence.split(separator):
            word = word.replace(thousands_separator, '')
            match = re.match(self.conf_log.find_word_year_regex, word)
            if is_digit(word) and not match and not single_digit_num_is_point_zero(word) and \
                    num_of_int_digits(word=word) >= self.conf_log.find_word_min_num_int_digits_in_searched_value:
                numbers.append(float(word))
        return numbers

    def get_table_values(self, text_line_object: LTTextLine, list_of_word_match_objects: List[XYWordMatch],
                         decimals: int) -> List[XYWordMatch]:
        word_coordinates_list = self.get_coordinates_of_word_in_text_line(
            text_line_object=text_line_object, decimals=decimals)
        if list_of_word_match_objects is not None:
            for word_match_in_list in list_of_word_match_objects:
                if word_coordinates_list is not None:
                    for x0, y0, x1, y1, word in word_coordinates_list:
                        # if word == 'Scope 1':
                        #     print(f'word: {word}, table values coordinates:{x0, y0, x1, y1}')
                        #     print('word_match_in_list.xx_coordinates_table_keyword_values_plus_tolerance:',
                        #           word_match_in_list.xx_coordinates_table_keyword_values_plus_tolerance)
                        #     print('word_match_in_list.yy_coordinates_table_keyword_values_plus_tolerance:',
                        #           word_match_in_list.yy_coordinates_table_keyword_values_plus_tolerance)
                        #     print('-----------------------------------------------------')
                        if word_match_in_list.are_table_keyword_x_coordinates_within_tolerance(xx0=x0, xx1=x1) and \
                                word_match_in_list.are_table_keyword_y_coordinates_within_tolerance(yy0=y0, yy1=y1):
                            # print('word_match_in_list.xx_coordinates_table_keyword_values_plus_tolerance:',
                            #       word_match_in_list.xx_coordinates_table_keyword_values_plus_tolerance)
                            # print('word_match_in_list.yy_coordinates_table_keyword_values_plus_tolerance:',
                            #       word_match_in_list.yy_coordinates_table_keyword_values_plus_tolerance)
                            # print(f'word: {word}, table values coordinates:{x0, y0, x1, y1}')
                            # print('-----------------------------------------------------')
                            word_match_in_list.add_table_values(word)
        return list_of_word_match_objects


def get_places_of_keyword_in_string(sentence: str, keyword: str, separator: str = ' ') -> list:
    """ This function will NOT return the index of the first word character in the sentence,
    but the x-th place(s) of a WORD in a sentence of words that are seperated by white spaces """
    all_places_of_keyword_in_sentence = list()
    for place_of_keyword_in_sentence, word in enumerate(sentence.split(separator)):
        if word.lower() == keyword.lower():
            all_places_of_keyword_in_sentence.append(place_of_keyword_in_sentence)
    return all_places_of_keyword_in_sentence


def get_first_last_indices_of_keyword_in_string(sentence: str, keyword: str) -> List[Tuple]:
    """ This function will return the start and end indices of a word in a string as list
    as multiple occurrences of the word are accounted for """
    start_end_index_set = set()
    for word in re.finditer(keyword, sentence):
        start_index = word.start()
        end_index = word.end()
        start_end_index_set.add((start_index, end_index))
    return list(start_end_index_set)


def get_first_last_indices_of_all_words_in_string(sentence: str) -> List[Tuple]:
    """ This function will return the start and end indices of ALL words in a string as a list of tuples """
    return [(element.start(), element.end()) for element in re.finditer(r'\S+', sentence)]


def is_digit(word: str) -> bool:
    try:
        float(word)
        return True
    except ValueError:
        return False


def num_of_int_digits(word: str or float) -> int:
    return int(math.log10(float(word))) + 1


def single_digit_num_is_point_zero(number: str or float) -> bool:
    return (num_of_int_digits(number) == 1) and (float(number) % 1 == 0)


def get_sentences_if_they_contain_words_of_two_search_lists(text_string: str, word_list_one: list, word_list_two: list) -> set:
    return set([sentence for sentence in text_string.split('.') for word in word_list_one if word in sentence for word in word_list_two if word in sentence])

