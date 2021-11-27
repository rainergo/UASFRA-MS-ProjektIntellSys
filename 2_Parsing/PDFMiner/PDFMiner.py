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

""" Documentation is here:
    https://pdfminersix.readthedocs.io/en/latest/index.html
"""


class PDFMiner:

    def __init__(self, path: str):
        self.path = open(path, 'rb')
        self.parser = PDFParser(self.path)
        self.document = PDFDocument(self.parser)
        self.rsrcmgr = PDFResourceManager()
        self.laparams = LAParams(line_overlap=0.5, char_margin=2.0, line_margin=0.5, word_margin=0.1, boxes_flow=0.0,
                                 detect_vertical=False, all_texts=True)
        # https://pdfminersix.readthedocs.io/en/latest/reference/composable.html#laparams
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

    def find_word(self, word: str, line_tolerance: float = 0.75):
        findings = list()
        page_number = 0
        for page in self.pages:
            coordinates = set()
            coordinates_plus_tolerance = set()
            page_number += 1
            # print('Processing next page...')
            self.interpreter.process_page(page)
            layout = self.page_aggregator.get_result()
            y0 = y1 = yy0 = yy1 = search_text = text = 0
            for first_layout_obj in layout:
                if isinstance(first_layout_obj, LTTextBox):
                    y0, y1, search_text = first_layout_obj.bbox[1], first_layout_obj.bbox[
                        3], first_layout_obj.get_text()
                    if word in search_text:
                        # print(f'At y-values {y0},{y1} text is: {search_text}')
                        coordinates.add((y0, y1))
                        y_tolerance = (y1 - y0) * line_tolerance
                        y0_lower = y0 - y_tolerance
                        y1_upper = y1 + y_tolerance
                        coordinates_plus_tolerance.add((y0_lower, y1_upper))
            if len(coordinates) > 0:
                finding = {'page_number': page_number, 'text': list()}
                for second_layout_obj in layout:
                    yy0, yy1 = second_layout_obj.bbox[1], second_layout_obj.bbox[3]
                    yy0_yy1_is_within_bounds = len(([(y_tol[0], y_tol[1]) for y_tol in coordinates_plus_tolerance if
                                                     (yy0 >= y_tol[0] and yy1 <= y_tol[1])])) > 0
                    if isinstance(second_layout_obj, LTTextBox) and ((yy0, yy1) in coordinates or (yy0_yy1_is_within_bounds)):
                        text = second_layout_obj.get_text().replace('\n', ' ').replace('  ', ' ')
                        # print(f'At yy-values {yy0},{yy1} text_2 is: {text}')
                        finding['text'].append(text)
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
