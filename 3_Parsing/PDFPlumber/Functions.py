import pdfplumber
import re
import pdftotext


def contains_word(search_words: list, sentence: str) -> bool:
    return any([word.lower() in sentence.lower() for word in search_words])


def get_pdfplumber_pages(path_to_pdf: str):
    pdf = pdfplumber.open(path_to_pdf)
    return pdf.pages


def get_pdftotext_pages(path_to_pdf: str):
    with open(path_to_pdf, "rb") as f:
        return pdftotext.PDF(f)


def get_pdfplumber_page_text(page) -> str:
    return page.extract_text()


def get_pdftotext_page_text(page) -> str:
    return page


def replace_substrings_in_string(replacements: dict, text: str) -> str:
    new_text = text
    for key, value in replacements.items():
        new_text = new_text.replace(key, value)
    return new_text


def split_text_into_sentences_separate_by_marks(text: str) -> list:
    regex = r'(?<!\w\.\w.)(?<![A-Z][a-z]\.)(?<=\.|\?|\!|\:)\s'
    return re.split(regex, text)


def split_text_into_sentences_separate_by_new_line(text: str) -> list:
    # regex = r'\n'
    return text.splitlines()