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
from itertools import islice
# from HelperFunctions import get_first_last_indices_of_keyword_in_string
from A_Configuration_and_Logs.conf_and_log import ConfLog

""" Documentation is here:
    https://pdfminersix.readthedocs.io/en/latest/index.html
"""


class XYWordMatch:
    """Class for keeping track of (coordinates for) Text objects that match the search word."""

    def __init__(self, x0: float, x1: float, y0: float, y1: float, neighbour_tolerance: float = 0.75,
                 table_x_tolerance: float = 0.75, table_y_tolerance: float = 0.75):
        self.neighbour_tolerance = neighbour_tolerance
        """ See comment in set_table_keyword_value_coordinates_plus_tolerance-method: """
        self.table_x_tolerance = table_x_tolerance
        self.table_y_tolerance = table_y_tolerance
        self.x_coordinates_plus_neighbour_tolerance = list()
        self.y_coordinates_plus_neighbour_tolerance = list()
        self.x_coordinates = (x0, x1)
        self.y_coordinates = (y0, y1)
        self.xx_coordinates_table_keyword_values_plus_tolerance = list()
        self.yy_coordinates_table_keyword_values_plus_tolerance = list()
        self.short_text_and_number = list()
        self.text_for_word2vec = list()
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

    def xx0_xx1_is_within_neighbour_bounds(self, xx0: float, xx1: float) -> bool:
        return len(([(x_tol[0], x_tol[1]) for x_tol in self.x_coordinates_plus_neighbour_tolerance if
                     (xx0 >= x_tol[0] and xx1 <= x_tol[1])])) > 0

    def yy0_yy1_is_within_neighbour_bounds(self, yy0: float, yy1: float) -> bool:
        return len(([(y_tol[0], y_tol[1]) for y_tol in self.y_coordinates_plus_neighbour_tolerance if
                     (yy0 >= y_tol[0] and yy1 <= y_tol[1])])) > 0

    def add_short_text_and_number(self, text: str):
        self.short_text_and_number.append(text)

    def add_text_for_word2vec(self, text: str):
        self.text_for_word2vec.append(text)

    def add_table_values(self, text: str):
        self.table_values.append(text)

    def _calc_y_neighbour_tolerance(self, y0: float, y1: float) -> tuple:
        y_tolerance = (y1 - y0) * self.neighbour_tolerance
        y0_lower = y0 - y_tolerance
        y1_upper = y1 + y_tolerance
        return y0_lower, y1_upper

    def _calc_x_neighbour_tolerance(self, x0: float, x1: float) -> tuple:
        x_tolerance = (x1 - x0) * self.neighbour_tolerance
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

    def are_table_keyword_coordinates_within_tolerance(self, xx0: float, xx1: float, yy0: float, yy1: float) -> bool:
        x_within_bounds = len(
            ([(x_tol[0], x_tol[1]) for x_tol in self.xx_coordinates_table_keyword_values_plus_tolerance if
              (xx0 >= x_tol[0] and xx1 <= x_tol[1])])) > 0
        y_within_bounds = len(
            ([(y_tol[0], y_tol[1]) for y_tol in self.yy_coordinates_table_keyword_values_plus_tolerance if
              (yy0 >= y_tol[0] and yy1 <= y_tol[1])])) > 0
        return x_within_bounds and y_within_bounds


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
                  neighbour_tolerance: float,
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
                word_match = None
                list_of_word_matches = list()
                set_of_table_coordinates = set()
                """ III. Iterate over all Text objects (called: text_container) on a page: """
                for text_container in all_layout_objects_on_one_page:
                    if isinstance(text_container, LTTextContainer) or isinstance(text_container, LTTextLine):
                        # ToDo: Get text into word2vec container/XYWordMatch
                        text_in_text_container = text_container.get_text()

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
                                                             neighbour_tolerance=neighbour_tolerance,
                                                             table_x_tolerance=table_x_tolerance,
                                                             table_y_tolerance=table_y_tolerance)
                                    list_of_word_matches.append(word_match)
                            """ Get xy-coordinates of table_keywords """
                            table_keyword_coordinates_in_text_line = self.get_coordinates_of_keyword(
                                text_line_object=text_line,
                                keywords_list=table_keywords)
                            if table_keyword_coordinates_in_text_line is not None:
                                set_of_table_coordinates.update(table_keyword_coordinates_in_text_line)

                print('list_of_word_matches:', list_of_word_matches)
                print('set_of_table_coordinates:', set_of_table_coordinates)


        #                             """ IV. Search starts here:
        #                             IV.A. Start from the page beginning and go through all objects (called: second_layout_obj) on
        #                             this page. The goal: Check if any of these second_layout_obj have the same y-coordinates
        #                             (height position) as the keyword(s). If so, store it,
        #                             together with the x-position of Text object that contains any of the 'table_keywords'
        #                             parameter: """
        #                             for second_layout_obj in all_layout_objects_on_one_page:
        #                                 if isinstance(second_layout_obj, LTTextContainer):
        #                                     """ Get individual lines of second_layout_obj, which is a Text object: """
        #                                     for text_line in second_layout_obj:
        #                                         if isinstance(text_line, LTTextLine) or isinstance(text_line,
        #                                                                                            LTTextLineHorizontal):
        #                                             xx0, yy0, xx1, yy1, text_table = \
        #                                                 self.get_coordinates(layout_obj=text_line, decimals=decimals)
        #                                             """ Get y-coordinates of keyword: """
        #                                             if any(word in text_table for word in keywords_list):
        #                                                 y0_keyword, y1_keyword = yy0, yy1
        #                                                 word_match.set_table_keyword_value_y_coordinates_plus_tolerance(
        #                                                     y0=y0_keyword,
        #                                                     y1=y1_keyword)
        #                                             """ Get x-coordinates of table_keyword: """
        #                                             if any(word in text_table for word in table_keywords) and \
        #                                                     len(text_table) < table_value_max_len:
        #                                                 x0_table_keyword, x1_table_keyword = xx0, xx1
        #                                                 word_match.set_table_keyword_value_x_coordinates_plus_tolerance(
        #                                                     x0=x0_table_keyword,
        #                                                     x1=x1_table_keyword)
        #                             """ IV.B. Start AGAIN from the page beginning and go through all objects
        #                             (called: second_layout_obj) on this page. The goal now: collect matching data: """
        #                             for second_layout_obj in all_layout_objects_on_one_page:
        #                                 if isinstance(second_layout_obj, LTTextContainer) or isinstance(
        #                                         second_layout_obj,
        #                                         LTTextLine):
        #                                     for text_line in second_layout_obj:
        #                                         if isinstance(text_line, LTTextLine) or isinstance(text_line,
        #                                                                                            LTTextLineHorizontal):
        #                                             xx0, yy0, xx1, yy1, text_found = self.get_coordinates(
        #                                                 layout_obj=text_line,
        #                                                 decimals=decimals)
        #                                             """ III.B.1. Check if any of these second_layout_obj have y-coordinates
        #                                             (height position) or x-coordinates (width position) that are nearby matches: """
        #                                             text_found_clean = text_found.replace('\n\n', '\n').replace('\n',
        #                                                                                                         ' ').strip()
        #                                             if word_match.xx0_xx1_is_within_neighbour_bounds(xx0=xx0,
        #                                                                                              xx1=xx1) and \
        #                                                     word_match.yy0_yy1_is_within_neighbour_bounds(yy0=yy0,
        #                                                                                                   yy1=yy1):
        #                                                 """ The text in these second_layout_obj must contain any of the words in the
        #                                                 parameter 'search_word_list' : """
        #                                                 matching_sentences_in_text_found = \
        #                                                     set([sentence for sentence in text_found_clean.split('.')
        #                                                          for word
        #                                                          in
        #                                                          search_word_list if word in sentence])
        #                                                 """ If the found text IS a numeric value OR contains a numeric value AND
        #                                                 Text and is NOT LONGER than the parameter 'short_text_max_len' (characters),
        #                                                 it is stored as 'short_text_and_number': """
        #                                                 match = re.match(self.conf_log.find_word_year_regex,
        #                                                                  text_found_clean)
        #                                                 if text_found_clean.replace(',', '').replace('.',
        #                                                                                              '').isdigit() and \
        #                                                         not match and len(
        #                                                     text_found_clean) >= self.conf_log.find_word_scope_value_minimum_characters_in_text:
        #                                                     word_match.add_short_text_and_number(text_found_clean)
        #                                                 elif any(term.replace(',', '').replace('.', '').isdigit() for
        #                                                          term in
        #                                                          text_found_clean) and any(
        #                                                     term.isascii() for term in text_found_clean) and len(
        #                                                     text_found_clean) < short_text_max_len:
        #                                                     for matching_sentence in matching_sentences_in_text_found:
        #                                                         word_match.add_short_text_and_number(matching_sentence)
        #                                                 else:
        #                                                     """ If the text is LONGER than short_text_max_len chars, we later might
        #                                                     try the word2vec approach: """
        #                                                     for matching_sentence in matching_sentences_in_text_found:
        #                                                         word_match.add_text_for_word2vec(matching_sentence)
        #
        #                                             """ IV.B.2. Check if any of these second_layout_obj have the same y-coordinates
        #                                             (height position) as the text_container (whose text might be the keyword) and x-position
        #                                             of LTTextBox-object that contains any of the 'table_keywords' parameter: """
        #                                             for text_line in second_layout_obj:
        #                                                 if isinstance(text_line, LTTextLine):
        #                                                     xx0, yy0, xx1, yy1, text_table = \
        #                                                         self.get_coordinates(layout_obj=text_line,
        #                                                                              decimals=decimals)
        #                                                     text_table_clean = text_table.replace('\n\n', '\n').replace(
        #                                                         '\n',
        #                                                         ' ').strip()
        #                                                     if word_match.are_table_keyword_coordinates_within_tolerance(
        #                                                             xx0=xx0,
        #                                                             xx1=xx1,
        #                                                             yy0=yy0,
        #                                                             yy1=yy1):
        #                                                         word_match.add_table_values(text_table_clean)
        #         """ Collect all data for each keyword_list """
        #         if word_match:
        #             keyword_finding = dict()
        #             keyword_finding['short_text_and_number'] = set()
        #             keyword_finding['text_for_word2vec'] = set()
        #             keyword_finding['table_values'] = set()
        #             for phrase in word_match.short_text_and_number:
        #                 keyword_finding['short_text_and_number'].add(phrase)
        #             for phrase in word_match.text_for_word2vec:
        #                 keyword_finding['text_for_word2vec'].add(phrase)
        #             for phrase in word_match.table_values:
        #                 keyword_finding['table_values'].add(phrase)
        #             if keyword_finding:
        #                 page_findings['page_number'] = page_number
        #                 page_findings[keywords_key] = keyword_finding
        #     """ Finally, append all keyword_list findings to an aggregated list ("findings"):"""
        #     if page_findings:
        #         findings.append(page_findings)
        # return findings

    def get_coordinates(self, layout_obj, decimals: int = 1):
        x0, y0, x1, y1, text_with_keyword = round(layout_obj.bbox[0], decimals), \
                                            round(layout_obj.bbox[1], decimals), \
                                            round(layout_obj.bbox[2], decimals), \
                                            round(layout_obj.bbox[3], decimals), \
                                            layout_obj.get_text()
        return x0, y0, x1, y1, text_with_keyword

    def get_year_and_fy(self) -> list or None:
        match = re.match(self.conf_log.find_word_year_regex, self.path)
        if match:
            word = match.group(1)
            return [word, 'FY' + word[-2:]]
        pages = extract_pages(self.path, page_numbers=[0], maxpages=1)
        for page in pages:
            for layout_obj in page:
                if isinstance(layout_obj, LTTextContainer) or isinstance(layout_obj, LTTextLine):
                    text = layout_obj.get_text()
                    word_list = text.split()
                    for word in word_list:
                        if len(word) == 4 and word.isdigit() and word.startswith('20'):
                            return [word, 'FY' + word[-2:]]
        return None

    def get_coordinates_of_keyword(self, text_line_object: LTTextLine, keywords_list: list, decimals: int = 1) -> \
            Set[Tuple] or None:
        if isinstance(text_line_object, LTTextLine):
            text_in_line = text_line_object.get_text()
            if any(word in text_in_line for word in keywords_list):
                keyword_coordinates_in_text_line = set()
                for keyword in keywords_list:
                    start_end_indices = get_first_last_indices_of_keyword_in_string(sentence=text_in_line,
                                                                                    keyword=keyword)
                    for start, end in start_end_indices:
                        word_start_and_end = list(islice(text_line_object, start, end))
                        """ There are some issues with strange fond types in some docs in which case None is returned """
                        x0 = round(word_start_and_end[0].bbox[0], decimals)
                        y0 = round(word_start_and_end[0].bbox[1], decimals)
                        x1 = round(word_start_and_end[-1].bbox[2], decimals)
                        y1 = round(word_start_and_end[-1].bbox[3], decimals)
                        keyword_coordinates_in_text_line.add((x0, y0, x1, y1))
                return keyword_coordinates_in_text_line if len(keyword_coordinates_in_text_line) > 0 else None
            else:
                return None


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
