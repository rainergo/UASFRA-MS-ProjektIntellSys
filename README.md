# General
This program parses, reads and extracts Key Performance Indicators (KPI) from a PDF document.
The software design can be best described as a Pipeline architecture as each step in the process
is executed sequentially and depends on the previous step. This is reflected in the naming of the
directories and files going from A_Configuration_and_logs all the way through G_main, in which a Jupyter Notebook
can execute the pipeline steps.
Each individual step is described by a separate README.md file in each of the directories.

## Information and Copyright
This program was designed by Rainer Gogel, Frankfurt in February 2022 as part of the module 
"Projekt Intelligente System" at the University of Applied Sciences in Frankfurt, Germany.
All rights reserved.

## How to run the program
### Step 1: 
This program heavily relies on the coordinates of text objects in a PDF document. As some PDF docs do not 
contain this positional metadata, they first need to be transformed.
Please see the README.md in "C_File_Conversion". If this transformation shall be done, please run the "transform_pdf()"-
function in "file_conversion.py". The source directory is "Annual_Reports", the target directory is 
"Annual_Reports_Converted", but can be changed in the "config.ini" file under [C_File_Conversion].

### Step 2:
Those PDF documents that shall be analyzed for KPIs must be stored in "Report_for_Analysis", but this also can be
changed in the "config.ini" file. 

### Step 3:
Which KPIs shall be searched? Please set this in "config.ini" under [D_Search][keyword_dict_of_lists] as list items
in this dictionary.
