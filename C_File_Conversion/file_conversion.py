import os
import subprocess
import logging
from A_Configuration_and_Logs.conf_and_log import ConfLog


def transform_pdf():
    conf_log = ConfLog()
    for orig_pdf in os.scandir(conf_log.path_to_input_directory):
        filename = os.fsdecode(orig_pdf)
        if filename.endswith(".pdf"):
            try:
                input_file_path_and_name_plus_suffix = os.path.abspath(orig_pdf)
                subprocess.run([conf_log.pdf24_tool, conf_log.pdf24_function, '-noProgress', '-outputDir',
                                conf_log.path_to_output_directory, '-profile', conf_log.pdf24_profile,
                                input_file_path_and_name_plus_suffix],
                               stderr=subprocess.DEVNULL)
            except Exception as e:
                logging.error(e, exc_info=True)
