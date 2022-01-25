# PDF24
    PDF conversion of non parsable PDF files into parsable PDF files is neccessary. In a converted PDF, we do not 
    only need the text, but also the exact layout and its coordinates of the non parsable PDF file which 
    we want to convert. PDF24 uses, among others, Tesseract to combine text with layout and writes both into a 
    new PDF file by using the command line tool "pdf24-DocTool.exe". 
    Documentation can be found here: https://creator.pdf24.org/manual/10/

### Installation of PDF24
    PDF24 ONLY works on Windows (Windows 10,etc), but NOT on Unix based systems (Linux, MacOS, etc.).
    In order to use PDF24, we obviousely need to install it first. There a two installers: .exe, .msi
    Please see: https://creator.pdf24.org/manual/10/
    We also need to include the executables of PDF24 in our 'PATH'. In my case: I just added
    "C:\Program Files(x86)\PDF24" to my Windows environment variables (German: "Umgebungsvariablen").

### pdf24-DocTool.exe
    pdf24-DocTool.exe is a command line tool to convert any file format (including PDF) into a new PDF file, 
    where both, text and layout are conserved.
    Here is a typical (in this case Windows Powershell) command to convert a non-parsable PDF into a parsable PDF:
``` 
PS C:\mydirectory> pdf24-DocTool -convertToPDF -noProgress -outputDir . -outputfile "out.pdf" -profile "default/best" "in.pdf"
```
    Function: -convertToPDF
    Flag: -noProgress -> Do not show the execution in a GUI / visually
    Flag: -profile -> Print quality. Please check docs.
    Flags: -outputDir and -outputfile should not be used together !!!
    Other flags: should be obvious from their name ... .