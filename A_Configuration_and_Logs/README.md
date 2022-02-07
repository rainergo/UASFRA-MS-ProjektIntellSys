## Configuration and Logs

This directory contains all the configuration files. Settings for the program should be made in the file
"config.ini". The settings there will affect the attributes of the class "ConfLog" in conf_and_log.py and thus
will facilitate to get settings into other Python files by just initiating an instance of class "ConfLog".
All logs are written to "error.log"

### Settings in the config.ini file
`path_to_reports_for_analysis_directory:`
The reports in this folder will be analyzed

`keyword_dict_of_lists:`
Which KPIs shall be searched? The values for the keys in this dictionary are the keywords for which the program will try 
to find values in the PDF doc.

`search_word_list:`
This is a filter for text sentences that later shall be used for text analysis. The keywords from the 
"keyword_dict_of_lists" above and any term in this "search_word_list" must be present. Otherwise, the sentences will not
be considered.

`year_regex:`
All terms in the text that have this regex pattern are considered years.

`unit_list:`
The terms in this list will be keywords in found sentences (see above: "search_word_list") and the most frequent term
in these sentences will be set as weight unit.

`neighbour_x_tolerance:`
Search for neighbours that positionally are within a certain search frame around the keyword. This value will determine 
the width (X-position or horizontal position) of the search frame distance to the keyword. 

`neighbour_y_tolerance:`
Search for neighbours that positionally are within a certain search frame around the keyword. This value will determine
the height (Y-position or vertical position) of the search frame distance to the keyword.

`table_x_tolerance:`
The XY-coordinates of the keyword value in a table with the year as header are calculated in the program. Sometimes
the height and width of the keyword value and the year (in the table header) differ due to different font sizes and the 
lengths of keyword value and year. The value set here adjusts the width of the keyword value x-coordinate.

`table_y_tolerance:`
The XY-coordinates of the keyword value in a table with the year as header are calculated in the program. Sometimes
the height and width of the keyword value and the year (in the table header) differ due to different font sizes and the
lengths of keyword value and year. The value set here adjusts the height of the keyword value y-coordinate.

`min_num_int_digits_in_searched_value:`
Exclude numbers in the search that have less than this setting for the keyword value (pre comma numbers).

`decimals:`
Round coordinates with this (after comma number) setting.

`D_Search.PDFMiner.LayoutOptions:`
All settings in this section will determine how the PDFMiner program will determine what a sentence, a word and a letter
is. Please read the docs: https://pdfminersix.readthedocs.io/en/latest/reference/composable.html#laparams
Default settings of my program differ from the default settings of PDFMiner for several reasons (but this would go
beyond the scope of this README.md).

`F_Extract:`
All settings in this section will determine how the results from the three different approaches (neighbours, table, 
text) in the program will be aggregated. The number set here determines how many of the most frequent numbers of each 
approach will go into the "aggregation pot" from which the most frequent values will be extracted as the final result.


All other settings in the "config.ini" file should be self-explaining.