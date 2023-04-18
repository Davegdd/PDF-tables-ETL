# PDF tables ETL

As a physics engineer I find myself constantly searching for tabular data in papers (smiconductor properties, biomaterials performances, efficiencies, etc.) and,
even though we have talking robots and flying cars, not being able to automatically extract all the tabular data in a PDF seems to still be a thing for some reason.
The best solution out there, and the one used in this method, is [Camelot](https://github.com/camelot-dev/camelot), but in my experience it will fail if the table is
not properly delimited by lines. So I came around with a solution which is manually and quickly drawing the lines of undetected tables using a supersimple GUI which
will allow Camelot to flawlessly extract the table. The process would be as follows:

- Place the script PDF_ETL.py in a folder and all the PDFs you want to extract tables from in a subfolder called "PDFs". 
You can also use the function `search_arxiv()` to find (e.g.`search_arxiv("superconductors review", max_results=10)`) and `download_pdfs(search)` 
to download PDFs about a specific topic from Arxiv.

```
root
├── PDFs
│   ├── pdf1
│   └── pdf2
│   └──...
│   └──pdfn
├── PDF_ETL.py
```

1. Run `process_papers()` and the code will extract in a list of dictionaries the __metadata__ (not the data yet) of the tables it found. You can use `scores` to see
this metadata which includes: table description, page, name of the PDF, etc. You can order the reuslts using NLP according to some keyword with `order_by()` 
(e.g. `order_by('semiconductor material properties')`), this will calculate a similarity score between the keyword and each table description.

2. Run `merge()` and a unique PDF (output.pdf) made up of all the pages with tables from the different PDFs will be created in the root folder.

3. Run `get_tables(PATH_TO_PDF)` on the previous PDF (e.g. in Google colab `get_tables('/content/output.pdf')`). This will output 2 files: output.xlsx which is an
excel file with all the tables that Camelot correctly extracted and output_to_annotate.pdf which is a PDF containing all the tables that could not be extracted.

4. Run `PDFViewer(PATH_TO_PDF)` on output_to_annotate.pdf (e.g. in Windows `PDFViewer('C:/Users/Dave/Desktop/root/output_to_annotate.pdf')`). A tkinter GUI window
will open: left click to draw a horizontal line, right click to draw a vertical line and right arrow to move to the next page. Just use those commands to mark the boundaries
of the tables and close the window when finished. Several .txt files with the boundaries coordinates will be automatically created in root.

5. Run `mark_tables(PATH_TO_PDF)` on output_to_annotate.pdf (e.g. in Windows `mark_tables('C:/Users/Dave/Desktop/root/output_to_annotate.pdf')`), this will use the
previously created .txt files to draw the tables and output a file (output_annotated.pdf) where all tables are correctly delimited by lines. Go back to step 3 with
this file and all the tables should be correctly extracted now.

