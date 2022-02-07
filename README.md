# Introduction
This program parses, reads and extracts Key Performance Indicators (KPI) from a PDF document.
The software design can be best described as a Pipeline architecture as each step in the process
is executed sequentially and depends on the previous step. This is reflected in the naming of the
directories and files going from A_Configuration_and_logs all the way through G_main, in which a Jupyter Notebook
can execute the pipeline steps by calling the method analyze_pdfs() (located in Rainer.F_Extract.Extract).
Any individual step, in addition to this README.md, might be described by a separate README.md file in each of the 
directories. 

## Information and Copyright
This program was designed by Rainer Gogel (rainer.gogel@web.de), Frankfurt in February 2022 as part of the module 
"Projekt Intelligente System" at the University of Applied Sciences in Frankfurt, Germany.
All rights reserved. No guarantees.


### General Information:
This program heavily relies on the coordinates of text objects in a PDF document. PDFMiner (the original program, not
my PDFMiner.py file) stores coordinates of Layout objects such as LTTextContainer, LTTextLine or LTChar. The XY origin is
at the bottom left corner where x = 0 and y = 0. The Layout objects are hierarchical and can be looped through. For 
instance, a LTTextContainer has LTTextLine objects which themselves have LTChar objects. All of these objects have their
own xy-coordinates.

My program has a threefold approach: 
Find neighbour values, find table values and extract values from matching sentences.

#### I. Find neighbours and extract values
    The XY-coordinates allow to search for positional neighbour layout objects. These neighbours might contain the searched
    keyword value if, for instance, the keyword and the keyword value appear in a graphic next to each other. 

#### II. Find table values
    PDF docs often contain tables which might or might not be recognizable by visual detection programs due to their
    lack of separation lines typically found in tables. My approach here is to first get the y-coordinates of the 
    keyword and the x-coordinates of the reporting year assuming this is the table column header and then search for 
    values with these xy-coordinates.

#### III. Extract values from sentences that match certain search criteria
    Matching sentences are sentences that contain the keyword and any other term from "search_word_list" in the 
    "config.ini" file. Then values that match certain criteria will be searched for in these matching sentences.

The program then aggregates the results of the three approaches and weighs them according to the parameters set under
[F_Extract] in the "config.ini" file. Please see the README.md under "A_Configuration_and_Logs".


## How to run the program
### Step 1: 
IMPORTANT: 
First, set the ABSOLUTE Path of the "config.ini" file  as "config_ini_path" parameter: 

    directory "A_Configuration_and_Logs"  -> "conf_and_log.py" file -> "config_ini_path" parameter 

Second, then also set the base_path variable as the absolute path to folder "Rainer" in the "config.ini" file:

    directory "A_Configuration_and_Logs"  -> "config.ini" file -> "base_path" parameter 

Then set the settings parameter. Please read the README.md in "A_Configuration_and_Logs".

### Step 2 (Optional):
    As some PDF docs do not contain positional metadata (i.e. coordinates), they first need to be transformed.
    Please see the README.md in "C_File_Conversion". If this transformation shall be done, please run the "transform_pdf()"-
    function in "file_conversion.py". The source directory is "Annual_Reports", the target directory is 
    "Annual_Reports_Converted", but this can be changed in the "config.ini" file under [C_File_Conversion].

### Step 3:
    Put all the PDF docs that you want to analyze into: "B_Reports.Reports_For_Analysis"

### Step 4:
    Run the program in G_MAIN. There is a Jupyter notebook in this directory which calls the "analyze_pdfs()" method from
    "F_Extract.Extract.py". The result can be displayed in a pandas DataFrame object whose method "to_csv" or "to_excel"
    will save the result in the directory and with the name specified as parameter in these methods. Of course, this call
    cann also be done from a Python file and called from the command line.
