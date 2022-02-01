from configparser import ConfigParser
import logging


class ConfLog:
    # Provide full absolute path to config.ini file:
    config_ini_path = 'D:/A_STUDIUM/PYTHON/UASFRA-MS-ProjektIntellSys/A_Configuration_and_Logs/config.ini'

    def __init__(self):
        self.config = ConfigParser()
        self.config.read(self.config_ini_path)
        self.logging_path = self.config['A_Configuration_and_Logs']['log_file_path_and_name']
        self.logging = logging
        self.logging.basicConfig(filename=self.logging_path, level=logging.ERROR,
                                 format='%(asctime)s %(message)s', datefmt='%m/%d/%Y %I:%M:%S %p')
        self.path_to_input_directory = self.config['C_File_Conversion']['path_to_input_directory']
        self.path_to_output_directory = self.config['C_File_Conversion']['path_to_output_directory']
        self.pdf24_tool = self.config['C_File_Conversion']['pdf24_tool']
        self.pdf24_function = self.config['C_File_Conversion']['pdf24_function']
        self.pdf24_profile = self.config['C_File_Conversion']['pdf24_profile']
        self.path_to_reports_for_analysis_directory = self.config['D_Search']['path_to_reports_for_analysis_directory']
        self.keyword_dict_of_lists = eval(self.config['D_Search']['keyword_dict_of_lists'])
        self.search_word_list = eval(self.config['D_Search']['search_word_list'])
        self.find_word_year_regex = eval(self.config['D_Search']['year_regex'])
        self.find_word_neighbour_tolerance = float(self.config['D_Search']['neighbour_tolerance'])
        self.find_word_table_x_tolerance = float(self.config['D_Search']['table_x_tolerance'])
        self.find_word_table_y_tolerance = float(self.config['D_Search']['table_y_tolerance'])
        self.find_word_table_value_max_len = int(self.config['D_Search']['table_value_max_len'])
        self.find_word_short_text_max_len = int(self.config['D_Search']['short_text_max_len'])
        self.find_word_scope_value_minimum_characters_in_text = int(
            self.config['D_Search']['scope_value_minimum_characters_in_text'])
        self.find_word_decimals = int(self.config['D_Search']['decimals'])
        self.pdfminer_layout_line_overlap = float(self.config['D_Search.PDFMiner.LayoutOptions']['line_overlap'])
        self.pdfminer_layout_char_margin = float(self.config['D_Search.PDFMiner.LayoutOptions']['char_margin'])
        self.pdfminer_layout_line_margin = float(self.config['D_Search.PDFMiner.LayoutOptions']['line_margin'])
        self.pdfminer_layout_word_margin = float(self.config['D_Search.PDFMiner.LayoutOptions']['word_margin'])
        self.pdfminer_layout_boxes_flow = float(self.config['D_Search.PDFMiner.LayoutOptions']['boxes_flow'])
        self.pdfminer_layout_detect_vertical = bool(self.config['D_Search.PDFMiner.LayoutOptions']['detect_vertical'])
        self.pdfminer_layout_all_texts = bool(self.config['D_Search.PDFMiner.LayoutOptions']['all_texts'])
