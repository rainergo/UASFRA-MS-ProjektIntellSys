from io import StringIO
from pdfminer.layout import LAParams, LTTextBox, LTTextLine, LTTextLineHorizontal
from pdfminer.pdfpage import PDFPage
from pdfminer.pdfinterp import PDFResourceManager
from pdfminer.pdfinterp import PDFPageInterpreter
from pdfminer.converter import PDFPageAggregator
from pdfminer.converter import TextConverter
from pdfminer.pdfdocument import PDFDocument
from pdfminer.pdftypes import resolve1
from pdfminer.pdfparser import PDFParser
from pdfminer.psparser import PSLiteral, PSKeyword
from pdfminer.utils import decode_text
from typing import List

""" Documentation is here:
    https://pdfminersix.readthedocs.io/en/latest/index.html
"""


class XYWordMatch:
    """Class for keeping track of (coordinates for) LTTextBoxes that match the search word."""

    # short_text_and_number = set()
    # text_for_word2vec = set()
    # table_values = set()

    def __init__(self, x0: float, x1: float, y0: float, y1: float, neighbour_tolerance: float = 0.75,
                 table_tolerance: float = 0.75):
        self.neighbour_tolerance = neighbour_tolerance
        self.table_tolerance = table_tolerance
        self.x_coordinates_plus_table_tolerance = list()
        self.x_coordinates_plus_neighbour_tolerance = list()
        self.y_coordinates_plus_neighbour_tolerance = list()
        self.x_coordinates = (x0, x1)
        self.y_coordinates = (y0, y1)
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
        self.x_coordinates_plus_table_tolerance.append(self._calc_x_table_tolerance(x0=x0, x1=x1))

    @property
    def y_coordinates(self) -> tuple:
        return self._y_coordinates

    @y_coordinates.setter
    def y_coordinates(self, value: tuple):
        y0, y1 = value
        self._y_coordinates = (y0, y1)
        self.y_coordinates_plus_neighbour_tolerance.append(self._calc_y_neighbour_tolerance(y0=y0, y1=y1))

    def xx0_xx1_is_within_table_bounds(self, xx0: float, xx1: float) -> bool:
        return len(([(x_tol[0], x_tol[1]) for x_tol in self.x_coordinates_plus_table_tolerance if
                     (xx0 >= x_tol[0] and xx1 <= x_tol[1])])) > 0

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

    def _calc_x_table_tolerance(self, x0: float, x1: float) -> tuple:
        x_tolerance = (x1 - x0) * self.table_tolerance
        x0_lower = x0
        x1_upper = x1 + x_tolerance
        return x0_lower, x1_upper


class PDFMiner:

    def __init__(self, path: str):
        self.path = open(path, 'rb')
        self.parser = PDFParser(self.path)
        self.document = PDFDocument(self.parser)
        self.resource_manager = PDFResourceManager()
        self.layout_params = LAParams(line_overlap=0.5, char_margin=2.0, line_margin=0.75, word_margin=0.1,
                                      boxes_flow=-1.0, detect_vertical=False, all_texts=True)
        # My settings:
        # (line_overlap=0.5, char_margin=2.0, line_margin=0.75, word_margin=0.1, boxes_flow=0.0,
        #                                  detect_vertical=False, all_texts=True)

        # Default settings:
        # (line_overlap=0.5, char_margin=2.0, line_margin=0.5, word_margin=0.1,
        #  boxes_flow=0.5, detect_vertical=False, all_texts=False)
        # Source: https://pdfminersix.readthedocs.io/en/latest/reference/composable.html#laparams
        self.page_aggregator = PDFPageAggregator(self.resource_manager, laparams=self.layout_params)
        self.interpreter = PDFPageInterpreter(self.resource_manager, self.page_aggregator)
        self.pages = PDFPage.get_pages(self.path)

    def process_pages(self):
        page_number = 0
        for page in self.pages:
            page_number += 1
            print('Processing next page...')
            self.interpreter.process_page(page)
            layout = self.page_aggregator.get_result()
            for lobj in layout:
                if isinstance(lobj, LTTextBox):
                    print('Type is:', type(lobj))
                    one, two, three, four, text = lobj.bbox[0], lobj.bbox[1], lobj.bbox[2], lobj.bbox[
                        3], lobj.get_text()
                    print(f'At {one}, {two}, {three}, {four} text is: {text}')

    def find_word(self, word: str, neighbour_tolerance: float = 0.00):
        findings = list()
        page_number = 0
        for page in self.pages:
            y_coordinates = set()
            y_coordinates_plus_neighbour_tolerance = set()
            x_coordinates = set()
            x_coordinates_plus_neighbour_tolerance = set()
            page_number += 1
            # print('Processing next page...')
            self.interpreter.process_page(page)
            layout = self.page_aggregator.get_result()
            # y0 = y1 = yy0 = yy1 = search_text = text = 0
            for first_layout_obj in layout:
                if isinstance(first_layout_obj, LTTextBox):
                    x0, y0, x1, y1, search_text = first_layout_obj.bbox[0], first_layout_obj.bbox[1], \
                                                  first_layout_obj.bbox[2], first_layout_obj.bbox[
                                                      3], first_layout_obj.get_text()
                    if word in search_text:
                        # print(f'At y-values {y0},{y1} text is: {search_text}')
                        y_coordinates.add((y0, y1))
                        y_tolerance = (y1 - y0) * neighbour_tolerance
                        y0_lower = y0 - y_tolerance
                        y1_upper = y1 + y_tolerance
                        y_coordinates_plus_neighbour_tolerance.add((y0_lower, y1_upper))
                        x_coordinates.add((x0, x1))
                        x_tolerance = (x1 - x0) * neighbour_tolerance
                        x0_lower = x0 - x_tolerance
                        x1_upper = x1 + x_tolerance
                        x_coordinates_plus_neighbour_tolerance.add((x0_lower, x1_upper))
            # Now we check if any y-coordinate (height position) of any other LTTextBox has same or nearby value
            # If yes, we merge the contents (text) of these LTTextBox-Objects into a string list
            if len(y_coordinates) > 0 or len(x_coordinates) > 0:
                finding = {'page_number': page_number, 'text': list()}
            if len(y_coordinates) > 0:
                for second_layout_obj in layout:
                    yy0, yy1 = second_layout_obj.bbox[1], second_layout_obj.bbox[3]
                    yy0_yy1_is_within_neighbour_bounds = len(
                        ([(y_tol[0], y_tol[1]) for y_tol in y_coordinates_plus_neighbour_tolerance if
                          (yy0 >= y_tol[0] and yy1 <= y_tol[1])])) > 0
                    if isinstance(second_layout_obj, LTTextBox) and (
                            (yy0, yy1) in y_coordinates or yy0_yy1_is_within_neighbour_bounds):
                        text = second_layout_obj.get_text().replace('\n', ' ').replace('  ', ' ')
                        # print(f'At yy-values {yy0},{yy1} text_2 is: {text}')
                        finding['text'].append(text)
                findings.append(finding)
            # Now we check if any x-coordinate (width position) of any other LTTextBox has same or nearby value
            # If yes, we merge the contents (text) of these LTTextBox-Objects into a string list
            if len(x_coordinates) > 0:
                for third_layout_obj in layout:
                    xx0, xx1 = third_layout_obj.bbox[0], third_layout_obj.bbox[2]
                    xx0_xx1_is_within_neighbour_bounds = len(
                        ([(x_tol[0], x_tol[1]) for x_tol in x_coordinates_plus_neighbour_tolerance if
                          (xx0 >= x_tol[0] and xx1 <= x_tol[1])])) > 0
                    if isinstance(third_layout_obj, LTTextBox) and (
                            (xx0, xx1) in y_coordinates or xx0_xx1_is_within_neighbour_bounds):
                        text = third_layout_obj.get_text().replace('\n', ' ').replace('  ', ' ')
                        # print(f'At xx-values {xx0},{xx1} text_3 is: {text}')
                        finding['text'].append(text)
                findings.append(finding)

        return findings

    def find_word_2(self, word: str, search_word_list: List[str], neighbour_tolerance: float = 0.00):
        findings = list()
        page_number = 0
        for page in self.pages:
            y_coordinates = set()
            y_coordinates_plus_neighbour_tolerance = set()
            x_coordinates = set()
            x_coordinates_plus_neighbour_tolerance = set()
            page_number += 1
            # print('Processing next page...')
            self.interpreter.process_page(page)
            layout = self.page_aggregator.get_result()
            y0 = y1 = yy0 = yy1 = search_text = text = 0
            # Iterate over all objects
            for first_layout_obj in layout:
                if isinstance(first_layout_obj, LTTextBox):
                    x0, y0, x1, y1, search_text = first_layout_obj.bbox[0], first_layout_obj.bbox[1], \
                                                  first_layout_obj.bbox[2], first_layout_obj.bbox[
                                                      3], first_layout_obj.get_text()
                    # If object is of type LTTextBox and word matches with content of this LTTextBox-object,
                    # then save x/y-coordinates individually
                    if word in search_text:
                        # print(f'At y-values {y0},{y1} text is: {search_text}')
                        y_coordinates.add((y0, y1))
                        y_tolerance = (y1 - y0) * neighbour_tolerance
                        y0_lower = y0 - y_tolerance
                        y1_upper = y1 + y_tolerance
                        y_coordinates_plus_neighbour_tolerance.add((y0_lower, y1_upper))
                        x_coordinates.add((x0, x1))
                        x_tolerance = (x1 - x0) * neighbour_tolerance
                        x0_lower = x0 - x_tolerance
                        x1_upper = x1 + x_tolerance
                        x_coordinates_plus_neighbour_tolerance.add((x0_lower, x1_upper))
            # Now we check if any y-coordinate (height position) or x-coordinate (width position)
            # of any other LTTextBox has same or nearby values. If yes, we merge the contents (text) of
            # these LTTextBox-Objects into a string list
            if len(y_coordinates) > 0 or len(x_coordinates) > 0:
                finding = {'page_number': page_number, 'text': list()}
                finding_raw = list()
                # Now we go through the exact same page but with the objective to find nearby LTTextBoxes
                for second_layout_obj in layout:
                    if isinstance(second_layout_obj, LTTextBox):
                        # Get all object coordinates
                        xx0, yy0, xx1, yy1 = second_layout_obj.bbox[0], second_layout_obj.bbox[1], \
                                             second_layout_obj.bbox[
                                                 2], second_layout_obj.bbox[3]
                        # Check if found object coordinates (+/- tolerance) match objects coordinates of objects
                        # that contain the searched word
                        yy0_yy1_is_within_neighbour_bounds = len(
                            ([(y_tol[0], y_tol[1]) for y_tol in y_coordinates_plus_neighbour_tolerance if
                              (yy0 >= y_tol[0] and yy1 <= y_tol[1])])) > 0
                        xx0_xx1_is_within_neighbour_bounds = len(
                            ([(x_tol[0], x_tol[1]) for x_tol in x_coordinates_plus_neighbour_tolerance if
                              (xx0 >= x_tol[0] and xx1 <= x_tol[1])])) > 0
                        # If so, then append this to the finding list
                        if ((yy0, yy1) in y_coordinates or yy0_yy1_is_within_neighbour_bounds) or (
                                (xx0, xx1) in x_coordinates or xx0_xx1_is_within_neighbour_bounds):
                            text = second_layout_obj.get_text().replace('\n', ' ').strip()
                            if page_number == 107:
                                print('text:', text)
                            finding_raw.append(text)
                            # if word_2 in text:
                            #     finding['text'].append(text)
                # First clean list according to word_list:
                finding['text'] = set([sentence for sentence in finding_raw for word in search_word_list if
                                       word in sentence.split() or sentence.replace('.', '', 1).replace(',', '',
                                                                                                        1).strip().isnumeric()])
                # finding['text'] = set([sentence for sentence in finding_raw for word in search_word_list if
                #                    word in sentence.split() or sentence.replace('.', '', 1).replace(',', '',
                #                                                                                     1).strip().isnumeric()])
                # Finally, append all cleaned finding lists into another list ("findings"):
                findings.append(finding)
        return findings

    def find_word_3(self, keywords: list, search_word_list: List[str], neighbour_tolerance: float,
                    table_tolerance: float, short_text_max_len: int = 20):
        findings = list()
        page_number = 0
        # I. Iterate over all pages
        for page in self.pages:
            page_number += 1
            self.interpreter.process_page(page)
            page_layout = self.page_aggregator.get_result()
            finding = {'page_number': None, 'short_text_and_number': set(), 'text_for_word2vec': set(),
                       'table_values': set()}
            # II. Iterate over all objects on a page
            for first_layout_obj in page_layout:
                if isinstance(first_layout_obj, LTTextBox):
                    text_with_keyword = first_layout_obj.get_text()
                    # If object is of type LTTextBox and word matches with content of this LTTextBox-object,
                    # then save x/y-coordinates individually
                    if any(word in text_with_keyword for word in keywords):
                        x0, y0, x1, y1 = first_layout_obj.bbox[0], first_layout_obj.bbox[1], \
                                         first_layout_obj.bbox[2], first_layout_obj.bbox[3]
                        ###################################################################################
                        word_match = XYWordMatch(x0=x0, x1=x1, y0=y0, y1=y1, neighbour_tolerance=neighbour_tolerance,
                                                 table_tolerance=table_tolerance)
                        ###################################################################################
                        text_with_keyword_clean = text_with_keyword.replace('\n\n', '\n').replace('\n', ' ').strip()

                        # Case 1: If the found string already contains the keyword and a number
                        # if any(term.isdigit() for term in text):
                        #     word_match.add_short_text_and_number(text)
                        ###################################################################################
                        # III. Search starts:
                        for second_layout_obj in page_layout:
                            # Now we check neighbour objects, i.e those objects whose y-coordinates
                            # (height position) or x-coordinates (width position) are nearby:
                            xx0, yy0, xx1, yy1 = second_layout_obj.bbox[0], second_layout_obj.bbox[1], \
                                                 second_layout_obj.bbox[2], second_layout_obj.bbox[3]

                            # IV. First, we get texts that might contain the keyword and keyword values:
                            if isinstance(second_layout_obj, LTTextBox):
                                if word_match.xx0_xx1_is_within_neighbour_bounds(xx0=xx0, xx1=xx1) or \
                                        word_match.yy0_yy1_is_within_neighbour_bounds(yy0=yy0, yy1=yy1):
                                    text_nearby = second_layout_obj.get_text()
                                    text_nearby_clean = text_nearby.replace('\n\n', '\n').replace('\n', ' ').strip()
                                    # We want to make sure that the text also contains a number, potentially
                                    # the keyword value:
                                    if any(term.isdigit() for term in text_nearby_clean):
                                        # Case 2: If both, the text_with_keyword and text_nearby
                                        # are SHORTER than short_text_max_len chars:
                                        if len(text_with_keyword_clean) < short_text_max_len and \
                                                len(text_nearby_clean) < short_text_max_len:
                                            word_match.add_short_text_and_number(text_nearby_clean)
                                            # word_match.add_short_text_and_number(
                                            #     text_with_keyword_clean + ' ' + text_nearby_clean)
                                        # Case 3: If the text is LONGER than short_text_max_len chars, we later might
                                        # try the word2vec approach:
                                        elif len(text_nearby_clean) >= short_text_max_len:
                                            matching_sentences_in_text_nearby = \
                                                set([sentence for sentence in text_nearby_clean.split('.') for word in
                                                     search_word_list if word in sentence])
                                            for matching_sentence in matching_sentences_in_text_nearby:
                                                word_match.add_text_for_word2vec(matching_sentence)
                                # V. Second, we get data that might be in a table:
                            if isinstance(second_layout_obj, LTTextBox):
                                if word_match.xx0_xx1_is_within_table_bounds(xx0=xx0, xx1=xx1):
                                    text_table = second_layout_obj.get_text()
                                    text_table_clean = text_table.replace('\n\n', '\n').replace('\n', ' ').strip()
                                    if any(term.isdigit() for term in text_table_clean):
                                        # Case 2: If both, the text_with_keyword and text_nearby
                                        # are SHORTER than short_text_max_len chars:
                                        if len(text_table_clean) < short_text_max_len:
                                            word_match.add_table_values(text_table_clean)

                        finding['page_number'] = page_number
                        for phrase in word_match.short_text_and_number:
                            finding['short_text_and_number'].add(phrase)
                        for phrase in word_match.text_for_word2vec:
                            finding['text_for_word2vec'].add(phrase)
                        for phrase in word_match.table_values:
                            finding['table_values'].add(phrase)
            # Finally, append all cleaned finding lists into another list ("findings"):
            if finding['page_number'] is not None:
                findings.append(finding)
        return findings

    def contains_digit(self, text: str):
        return any(word.isdigit() for word in text)
