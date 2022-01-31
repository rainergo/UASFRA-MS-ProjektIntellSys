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
