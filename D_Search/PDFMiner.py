from io import StringIO
from pdfminer.layout import LAParams, LTTextBox, LTTextContainer, LTTextLine, LTTextLineHorizontal
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
from typing import List, Dict
import re

""" Documentation is here:
    https://pdfminersix.readthedocs.io/en/latest/index.html
"""


class XYWordMatch:
    """Class for keeping track of (coordinates for) LTTextBoxes that match the search word."""

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
        self.layout_params = LAParams(line_overlap=0.5, char_margin=2.0, line_margin=0.75, word_margin=0.1,
                                      boxes_flow=0.0, detect_vertical=False, all_texts=True)
        # Instead of a page_aggregator, a TextConverter-Instance could be passed to the self.interpreter:
        # self.output_string = StringIO()
        # self.text_converter = TextConverter(rsrcmgr=self.resource_manager, outfp=self.output_string,
        #                                     laparams=self.layout_params)

        self.device = TextConverter(rsrcmgr=self.resource_manager, outfp=StringIO(), laparams=self.layout_params)
        self.page_aggregator = PDFPageAggregator(rsrcmgr=self.resource_manager, laparams=self.layout_params)
        self.interpreter = PDFPageInterpreter(self.resource_manager, self.device)
        # self.interpreter = PDFPageInterpreter(self.resource_manager, self.page_aggregator)
        self.pages = PDFPage.get_pages(fp=self.stream, pagenos=None, maxpages=0, password='',
                                       caching=True, check_extractable=False)
        self.pages = extract_pages(pdf_file=path, laparams=self.layout_params)
        # self.pages = PDFPage.create_pages(self.document)

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

    def find_word(self, keywords_dict_of_list: Dict[str, List[str]], search_word_list: List[str], neighbour_tolerance: float,
                  table_keywords: List[str], table_x_tolerance: float = 3.50, table_y_tolerance: float = 0.25,
                  table_value_max_len: int = 12, short_text_max_len: int = 50, decimals: int = 1):
        if not self.doc_is_extractable:
            raise PDFTextExtractionNotAllowed('The document does not allow extraction ! ')
        findings = list()
        page_number = 0
        """ I. Iterate over all pages: """
        for page_layout in self.pages:
            page_number += 1
            page_findings = dict()
            """ II. Iterate over all keyword_lists in the keyword_list_of_lists: """
            for keywords_key, keywords_list in keywords_dict_of_list.items():
                word_match = None
                """ III. Iterate over all Text objects (called: first_layout_obj) on a page: """
                for first_layout_obj in page_layout:
                    if isinstance(first_layout_obj, LTTextContainer) or isinstance(first_layout_obj, LTTextLine):
                        x0, y0, x1, y1, text_with_keyword = self.get_coordinates(layout_obj=first_layout_obj,
                                                                                 decimals=decimals)
                        """ If keyword matches content of this LTTextBox-object, then initiate the data carrier object
                        (XYWordMatch-instance) and store position data there: """
                        if any(word in text_with_keyword for word in keywords_list):
                            word_match = XYWordMatch(x0=x0, x1=x1, y0=y0, y1=y1, neighbour_tolerance=neighbour_tolerance,
                                                     table_x_tolerance=table_x_tolerance,
                                                     table_y_tolerance=table_y_tolerance)
                            """ IV. Search starts here: 
                            IV.A. Start from the page beginning and go through all objects (called: second_layout_obj) on 
                            this page. The goal: Check if any of these second_layout_obj have the same y-coordinates 
                            (height position) as the first_layout_obj (whose text contains the keyword). If so, store it, 
                            together with the x-position of LTTextBox-object that contains any of the 'table_keywords' 
                            parameter: """
                            for second_layout_obj in page_layout:
                                if isinstance(second_layout_obj, LTTextContainer):
                                    """ Get individual lines of second_layout_obj, which is a LTTextBox: """
                                    for line in second_layout_obj:
                                        if isinstance(line, LTTextLine) or isinstance(line, LTTextLineHorizontal):
                                            xx0, yy0, xx1, yy1, text_table = \
                                                self.get_coordinates(layout_obj=line, decimals=decimals)
                                            """ Get y-coordinates of keyword: """
                                            if any(word in text_table for word in keywords_list):
                                                ########################
                                                # print(f'page: {page_number}, text_table for keyword:{text_table}')
                                                ####################
                                                y0_keyword, y1_keyword = yy0, yy1
                                                word_match.set_table_keyword_value_y_coordinates_plus_tolerance(
                                                    y0=y0_keyword,
                                                    y1=y1_keyword)
                                            """ Get x-coordinates of table_keyword: """
                                            if any(word in text_table for word in table_keywords) and \
                                                    len(text_table) < table_value_max_len:
                                                ########################
                                                # print(f'page: {page_number}, text_table for table_keyword:{text_table}')
                                                ####################
                                                x0_table_keyword, x1_table_keyword = xx0, xx1
                                                word_match.set_table_keyword_value_x_coordinates_plus_tolerance(
                                                    x0=x0_table_keyword,
                                                    x1=x1_table_keyword)
                            """ IV.B. Start AGAIN from the page beginning and go through all objects 
                            (called: second_layout_obj) on this page. The goal now: collect matching data: """
                            for second_layout_obj in page_layout:
                                if isinstance(second_layout_obj, LTTextContainer) or isinstance(second_layout_obj,
                                                                                                LTTextLine):
                                    xx0, yy0, xx1, yy1, text_found = self.get_coordinates(layout_obj=second_layout_obj,
                                                                                          decimals=decimals)
                                    """ III.B.1. Check if any of these second_layout_obj have y-coordinates
                                    (height position) or x-coordinates (width position) that are nearby: """
                                    text_found_clean = text_found.replace('\n\n', '\n').replace('\n', ' ').strip()
                                    if word_match.xx0_xx1_is_within_neighbour_bounds(xx0=xx0, xx1=xx1) or \
                                            word_match.yy0_yy1_is_within_neighbour_bounds(yy0=yy0, yy1=yy1):

                                        """ The text in these second_layout_obj must contain any of the words in the 
                                        parameter 'search_word_list' : """
                                        matching_sentences_in_text_found = \
                                            set([sentence for sentence in text_found_clean.split('.') for word in
                                                 search_word_list if word in sentence])
                                        """ If the found text contains a numeric value and is NOT LONGER than the parameter
                                        'short_text_max_len' (characters), it is stored as 'short_text_and_number': """
                                        if any(term.isdigit() for term in text_found_clean) and any(
                                                term.isascii() for term in text_found_clean) and len(
                                            text_found_clean) < short_text_max_len:
                                            for matching_sentence in matching_sentences_in_text_found:
                                                word_match.add_short_text_and_number(matching_sentence)
                                        else:
                                            """ If the text is LONGER than short_text_max_len chars, we later might
                                            try the word2vec approach: """
                                            for matching_sentence in matching_sentences_in_text_found:
                                                word_match.add_text_for_word2vec(matching_sentence)

                                    """ IV.B.2. Check if any of these second_layout_obj have the same y-coordinates
                                    (height position) as the first_layout_obj (whose text might be the keyword) and x-position
                                    of LTTextBox-object that contains any of the 'table_keywords' parameter: """
                                    for line in second_layout_obj:
                                        if isinstance(line, LTTextLine):
                                            xx0, yy0, xx1, yy1, text_table = \
                                                self.get_coordinates(layout_obj=line, decimals=decimals)
                                            text_table_clean = text_table.replace('\n\n', '\n').replace('\n', ' ').strip()
                                            if word_match.are_table_keyword_coordinates_within_tolerance(xx0=xx0, xx1=xx1,
                                                                                                         yy0=yy0, yy1=yy1):
                                                word_match.add_table_values(text_table_clean)
                """ Collect all data for each keyword_list """
                if word_match:
                    keyword_finding = dict()
                    keyword_finding['short_text_and_number'] = set()
                    keyword_finding['text_for_word2vec'] = set()
                    keyword_finding['table_values'] = set()
                    for phrase in word_match.short_text_and_number:
                        keyword_finding['short_text_and_number'].add(phrase)
                    for phrase in word_match.text_for_word2vec:
                        keyword_finding['text_for_word2vec'].add(phrase)
                    for phrase in word_match.table_values:
                        keyword_finding['table_values'].add(phrase)
                    if keyword_finding:
                        page_findings['page_number'] = page_number
                        page_findings[keywords_key] = keyword_finding
            """ Finally, append all keyword_list findings to an aggregated list ("findings"):"""
            if page_findings:
                findings.append(page_findings)
        return findings

    def get_coordinates(self, layout_obj, decimals: int = 1):
        x0, y0, x1, y1, text_with_keyword = round(layout_obj.bbox[0], decimals), \
                                            round(layout_obj.bbox[1], decimals), \
                                            round(layout_obj.bbox[2], decimals), \
                                            round(layout_obj.bbox[3], decimals), \
                                            layout_obj.get_text()
        return x0, y0, x1, y1, text_with_keyword

    def get_year_and_fy(self) -> list or None:
        word = re.match(r'.*([2][0][1-2][0-9])', self.path)
        if word:
            return word.group(1)
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
