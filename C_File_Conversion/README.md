# PDF24
    To detect layout objects and coordinates in a PDF file where the layout information is not stored in its Metadata, 
    a transformation that adds this kind of Metadata to a newly created PDF file is neccessary. In a transformed PDF, 
    we thus do not only need the text of the original PDF file, but also its exact layout objects and its coordinates. 
    PDF24 uses, among others, Tesseract to combine text with layout and writes both into a new PDF file by using the 
    command line tool "pdf24-DocTool.exe". Documentation can be found here: https://creator.pdf24.org/manual/10/

### Installation of PDF24
    PDF24 ONLY works on Windows (Windows 10,etc), but NOT on Unix based systems (Linux, MacOS, etc.).
    In order to use PDF24, we obviousely need to install it first. There a two installers: .exe, .msi
    Please see: https://creator.pdf24.org/manual/10/
    We also need to include the executables of PDF24 in our 'PATH'. In my case: I just added
    "C:\Program Files(x86)\PDF24" to my Windows environment variables (German: "Umgebungsvariablen").

### pdf24-DocTool.exe
    pdf24-DocTool.exe is a command line tool to convert any file format (including PDF) into a new PDF file. 
    Both, the text and layout objects/coordinates are conserved or newly created if they were not stored in
    the Metadata of the original file.
    Here is a typical (in this case Windows Powershell) command to convert a layout-less PDF into a PDF with layout 
    information:
``` 
PS C:\mydirectory> pdf24-DocTool -convertToPDF -noProgress -outputDir . -outputfile "out.pdf" -profile "default/best" "in.pdf"
```
    Function: -convertToPDF
    Flag: -noProgress -> Do not show the execution in a GUI / visually
    Flag: -profile -> Print quality. Please check docs.
    Flags: -outputDir and -outputfile should not be used together !!!
    Other flags: should be obvious from their name ... .
    
### Conversion process
    As we do not know which PDF files contain the layout in its Metadata, with the Python function 'transform_pdf()'
    in the 'file_conversion.py', we will do the transformation for every PDF in the "/1_Reports/Annual_Reports" folder 
    and store it in the "../1_Reports/Annual_Reports_Converted" folder.