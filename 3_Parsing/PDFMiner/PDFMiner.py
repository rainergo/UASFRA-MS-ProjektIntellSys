from io import StringIO
from pdfminer.layout import LAParams, LTTextBox
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


class PDFMiner:

    def __init__(self, path: str):
        self.path = open(path, 'rb')
        self.parser = PDFParser(self.path)
        self.document = PDFDocument(self.parser)
        self.rsrcmgr = PDFResourceManager()
        self.laparams = LAParams(line_overlap=0.5, char_margin=2.0, line_margin=0.75, word_margin=0.1,
                                 boxes_flow=0.5, detect_vertical=False, all_texts=True)
        # My settings:
        # (line_overlap=0.5, char_margin=2.0, line_margin=0.75, word_margin=0.1, boxes_flow=0.0,
        #                                  detect_vertical=False, all_texts=True)

        # Default settings:
        # (line_overlap=0.5, char_margin=2.0, line_margin=0.5, word_margin=0.1,
        #  boxes_flow=0.5, detect_vertical=False, all_texts=False)
        # Source: https://pdfminersix.readthedocs.io/en/latest/reference/composable.html#laparams
        self.page_aggregator = PDFPageAggregator(self.rsrcmgr, laparams=self.laparams)
        self.interpreter = PDFPageInterpreter(self.rsrcmgr, self.page_aggregator)
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

    def find_word(self, word: str, line_tolerance: float = 0.00):
        findings = list()
        page_number = 0
        for page in self.pages:
            y_coordinates = set()
            y_coordinates_plus_tolerance = set()
            x_coordinates = set()
            x_coordinates_plus_tolerance = set()
            page_number += 1
            # print('Processing next page...')
            self.interpreter.process_page(page)
            layout = self.page_aggregator.get_result()
            y0 = y1 = yy0 = yy1 = search_text = text = 0
            for first_layout_obj in layout:
                if isinstance(first_layout_obj, LTTextBox):
                    x0, y0, x1, y1, search_text = first_layout_obj.bbox[0], first_layout_obj.bbox[1], \
                                                  first_layout_obj.bbox[2], first_layout_obj.bbox[
                                                      3], first_layout_obj.get_text()
                    if word in search_text:
                        # print(f'At y-values {y0},{y1} text is: {search_text}')
                        y_coordinates.add((y0, y1))
                        y_tolerance = (y1 - y0) * line_tolerance
                        y0_lower = y0 - y_tolerance
                        y1_upper = y1 + y_tolerance
                        y_coordinates_plus_tolerance.add((y0_lower, y1_upper))
                        x_coordinates.add((x0, x1))
                        x_tolerance = (x1 - x0) * line_tolerance
                        x0_lower = x0 - x_tolerance
                        x1_upper = x1 + x_tolerance
                        x_coordinates_plus_tolerance.add((x0_lower, x1_upper))
            # Now we check if any y-coordinate (height position) of any other LTTextBox has same or nearby value
            # If yes, we merge the contents (text) of these LTTextBox-Objects into a string list
            if len(y_coordinates) > 0 or len(x_coordinates) > 0:
                finding = {'page_number': page_number, 'text': list()}
            if len(y_coordinates) > 0:
                for second_layout_obj in layout:
                    yy0, yy1 = second_layout_obj.bbox[1], second_layout_obj.bbox[3]
                    yy0_yy1_is_within_bounds = len(([(y_tol[0], y_tol[1]) for y_tol in y_coordinates_plus_tolerance if
                                                     (yy0 >= y_tol[0] and yy1 <= y_tol[1])])) > 0
                    if isinstance(second_layout_obj, LTTextBox) and (
                            (yy0, yy1) in y_coordinates or yy0_yy1_is_within_bounds):
                        text = second_layout_obj.get_text().replace('\n', ' ').replace('  ', ' ')
                        # print(f'At yy-values {yy0},{yy1} text_2 is: {text}')
                        finding['text'].append(text)
                findings.append(finding)
            # Now we check if any x-coordinate (width position) of any other LTTextBox has same or nearby value
            # If yes, we merge the contents (text) of these LTTextBox-Objects into a string list
            if len(x_coordinates) > 0:
                for third_layout_obj in layout:
                    xx0, xx1 = third_layout_obj.bbox[0], third_layout_obj.bbox[2]
                    xx0_xx1_is_within_bounds = len(([(x_tol[0], x_tol[1]) for x_tol in x_coordinates_plus_tolerance if
                                                     (xx0 >= x_tol[0] and xx1 <= x_tol[1])])) > 0
                    if isinstance(third_layout_obj, LTTextBox) and (
                            (xx0, xx1) in y_coordinates or xx0_xx1_is_within_bounds):
                        text = third_layout_obj.get_text().replace('\n', ' ').replace('  ', ' ')
                        # print(f'At xx-values {xx0},{xx1} text_3 is: {text}')
                        finding['text'].append(text)
                findings.append(finding)

        return findings

    def find_word_2(self, word: str, search_word_list: List[str], line_tolerance: float = 0.00):
        findings = list()
        page_number = 0
        for page in self.pages:
            y_coordinates = set()
            y_coordinates_plus_tolerance = set()
            x_coordinates = set()
            x_coordinates_plus_tolerance = set()
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
                        y_tolerance = (y1 - y0) * line_tolerance
                        y0_lower = y0 - y_tolerance
                        y1_upper = y1 + y_tolerance
                        y_coordinates_plus_tolerance.add((y0_lower, y1_upper))
                        x_coordinates.add((x0, x1))
                        x_tolerance = (x1 - x0) * line_tolerance
                        x0_lower = x0 - x_tolerance
                        x1_upper = x1 + x_tolerance
                        x_coordinates_plus_tolerance.add((x0_lower, x1_upper))
            # Now we check if any y-coordinate (height position) or x-coordinate (width position)
            # of any other LTTextBox has same or nearby values. If yes, we merge the contents (text) of
            # these LTTextBox-Objects into a string list
            if len(y_coordinates) > 0 or len(x_coordinates) > 0:
                finding = {'page_number': page_number, 'text': list()}
                for second_layout_obj in layout:
                    if isinstance(second_layout_obj, LTTextBox):
                        # Get all object coordinates
                        xx0, yy0, xx1, yy1 = second_layout_obj.bbox[0], second_layout_obj.bbox[1], \
                                             second_layout_obj.bbox[
                                                 2], second_layout_obj.bbox[3]
                        # Check if found object coordinates (+/- tolerance) match objects coordinates of objects
                        # that contain the searched word
                        yy0_yy1_is_within_bounds = len(
                            ([(y_tol[0], y_tol[1]) for y_tol in y_coordinates_plus_tolerance if
                              (yy0 >= y_tol[0] and yy1 <= y_tol[1])])) > 0
                        xx0_xx1_is_within_bounds = len(
                            ([(x_tol[0], x_tol[1]) for x_tol in x_coordinates_plus_tolerance if
                              (xx0 >= x_tol[0] and xx1 <= x_tol[1])])) > 0
                        # If so, then append this to the finding list
                        if ((yy0, yy1) in y_coordinates or yy0_yy1_is_within_bounds) or (
                                (xx0, xx1) in y_coordinates or xx0_xx1_is_within_bounds):
                            text = second_layout_obj.get_text().replace('\n', ' ').replace('  ', ' ')
                            finding['text'].append(text)
                            # if word_2 in text:
                            #     finding['text'].append(text)
                # First clean list according to word_list:
                finding['text'] = set([sentence for sentence in finding['text'] for word in search_word_list if
                                   word in sentence.split() or sentence.replace('.', '', 1).replace(',', '',
                                                                                                    1).strip().isnumeric()])
                # Finally, append all cleaned finding lists into another list ("findings"):
                findings.append(finding)
        return findings

    def extract_text(self):
        output_string = StringIO()
        device = TextConverter(self.rsrcmgr, output_string, laparams=self.laparams)
        interpreter = PDFPageInterpreter(self.rsrcmgr, device)
        for page in PDFPage.create_pages(self.document):
            interpreter.process_page(page)
        print(output_string.getvalue())

    def decode_value(self, value):
        # decode PSLiteral, PSKeyword
        if isinstance(value, (PSLiteral, PSKeyword)):
            value = value.name
        # decode bytes
        if isinstance(value, bytes):
            value = decode_text(value)
        return value

    def resolve_acroforms(self):
        data = {}
        res = resolve1(self.document.catalog)
        if 'AcroForm' not in res:
            raise ValueError("No AcroForm Found")
        fields = resolve1(self.document.catalog['AcroForm'])['Fields']  # may need further resolving
        for f in fields:
            field = resolve1(f)
            name, values = field.get('T'), field.get('V')
            # decode name
            name = decode_text(name)
            # resolve indirect obj
            values = resolve1(values)
            # decode value(s)
            if isinstance(values, list):
                values = [self.decode_value(v) for v in values]
            else:
                values = self.decode_value(values)
            data.update({name: values})
            print(name, values)
