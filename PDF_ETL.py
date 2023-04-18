"""
Created on Mon Mar 13 12:27:06 2023

@author: Dave
"""
import fitz
from PIL import Image, ImageTk
import tkinter as tk
import numpy as np
import arxiv 
import os
import re
import spacy
import camelot
import pandas as pd
from multiprocessing.pool import ThreadPool as Pool
import pprint


try:
    nlp = spacy.load("en_core_web_lg")
except:
    spacy.cli.download("en_core_web_lg")
    nlp = spacy.load("en_core_web_lg")

descriptions = []
scores = []

def search_arxiv(query, max_results=10):
    search = arxiv.Search(
        query=query,
        max_results=max_results,
        sort_by=arxiv.SortCriterion.Relevance
    )
    
    titles = [result.title for result in search.results()]
    pprint.pprint(titles)
    return search


def download(result):
    try:
        result.download_pdf(dirpath="./PDFs")
    except:
        print(result.title + ' failed to download.')

def download_pdfs(search):
    with Pool() as pool:
        pool.map(download, search.results())


# Extract footers of tables
def process_each(paper):
    try:
        doc = fitz.open('./PDFs/' + paper)
        pages = [page.get_text('blocks') for page in doc]
        descriptions = []
        for page_number, page in enumerate(pages):
            for block in page:
                if re.findall('Table \d{1,2}[.:]', block[4][:9]): #TODO: improve to get different formats
                    descriptions.append(({'Item': block[4][:9], 'Text': block[4][9:], 'Page': page_number + 1,
                                      'Document': os.path.splitext(paper)[0]}))
        return descriptions
    except:
        print('Cannot open ' + paper)
        return []

def process_papers():
    global descriptions
    descriptions.clear()
    with Pool() as pool:
        results = pool.map(process_each, os.listdir('./PDFs/'))
        descriptions = [desc for res in results for desc in res]
        order_by('')

def order_by(text):
    global scores
    global descriptions
    scores.clear()
    for i in range(len(descriptions)):
        score = nlp(descriptions[i]['Text']).similarity(nlp(text))
        scores.append(('Similarity: ' + str(score), descriptions[i]))
    scores.sort(key=lambda elem: elem[0], reverse=True)
    return scores

def merge():
    global scores
    output_pdf = fitz.open()
    for score in scores:
        file_path = './PDFs/' + score[1]['Document'] + '.pdf'
        doc = fitz.open(file_path)
        page = doc[score[1]['Page'] - 1]
        output_pdf.insert_pdf(doc, from_page=page.number, to_page=page.number, links =False, annots=False)
    output_pdf.save('output.pdf')

def get_tables(pdf):   
    tables = camelot.read_pdf(pdf, pages='all', flavor='lattice', flag_size = True)
    # Check if empty tables were extracted
    empty_tables = []
    for t in range(len(tables)):
      if tables[t].df.applymap(lambda x: x == '').all().all():
        empty_tables.append(t)

    succesful_tables = [tables[i] for i in range(len(tables)) if i not in empty_tables]
    pages_to_remove = list(set([succesful_tables[i].page for i in range(len(succesful_tables))]))

    # Sort the list in descending order to avoid index changes
    pages_to_remove.sort(reverse=True)

    # Remove the pages
    output_pdf = fitz.open(pdf)
    for page_num in pages_to_remove:
        output_pdf.delete_page(page_num-1)

    output_pdf.save('output_to_annotate.pdf')
    output_pdf.close()

    # Create a Pandas Excel writer using xlsxwriter as the engine
    writer = pd.ExcelWriter('output.xlsx', engine='xlsxwriter')

    # Write each DataFrame to a different sheet
    for i, tb in enumerate(succesful_tables):
        tb.df.to_excel(writer, sheet_name=f'Sheet{i+1}', index=False)

    # Save the Excel file
    writer.save()


class PDFViewer:
    def __init__(self, pdf_file):
        self.pdf_file = pdf_file
        self.doc = fitz.open(pdf_file)
        self.current_page = 0
        
        self.root = tk.Tk()
        self.root.title("PDF Viewer")
        self.root.bind("<Return>", self.next_page)
        self.root.bind("<Right>", self.next_page)
        self.root.bind("<Left>", self.prev_page)
        self.root.bind("<Button-1>", self.add_horizontal_line)
        self.root.bind("<Button-3>", self.add_vertical_line)
        
        self.canvas = tk.Canvas(self.root, width=900, height=1000)
        self.canvas.pack()
        
        self.render_page()
        self.root.mainloop()
        
    def render_page(self):
        page = self.doc[self.current_page]
        pix = page.get_pixmap()
        img = Image.frombytes("RGB", [pix.width, pix.height], pix.samples)
        img = img.resize((900, 1000))
        self.photo = ImageTk.PhotoImage(img)
        self.canvas.create_image(0, 0, image=self.photo, anchor="nw")
        
    def next_page(self, event):
        if self.current_page < len(self.doc) - 1:
            self.save_lines_to_file()
            self.current_page += 1
            self.canvas.delete("all")
            self.render_page()
            
    def prev_page(self, event):
        if self.current_page > 0:
            self.save_lines_to_file()
            self.current_page -= 1
            self.canvas.delete("all")
            self.render_page()
            
    def add_horizontal_line(self, event):
        x1, y1 = (0, event.y)
        x2, y2 = (self.canvas.winfo_width(), event.y)
        self.canvas.create_line(x1, y1, x2, y2, fill="red")
        self.save_lines_to_file()
        
    def add_vertical_line(self, event):
        x1, y1 = (event.x, 0)
        x2, y2 = (event.x, self.canvas.winfo_height())
        self.canvas.create_line(x1, y1, x2, y2, fill="blue")
        self.save_lines_to_file()
        
    def save_lines_to_file(self):
        lines = self.canvas.find_all()
        if len(lines) > 0:
            with open(f"{self.pdf_file[:-4]}_{self.current_page}_lines.txt", "w") as f:
                for item in lines:
                    if self.canvas.type(item) == "line":
                        coords = self.canvas.coords(item)
                        f.write(f"{(coords[0])}, {(coords[1])}, {(coords[2])}, {(coords[3])}\n")


def mark_tables(pdf):
    
    doc = fitz.open(pdf)
    
    # Get the number of pages
    pages = doc.page_count
    
    for page in range(pages):
        
      try:
        # Read line coordinates from file
        with open(f'{pdf[:-4]}_{page}_lines.txt', 'r') as f:
            lines = f.readlines()
        
        # Separate horizontal and vertical lines and extract coordinates
        h_lines = []
        v_lines = []
        for line in lines:
            direction = line.split(',', 1)[0]
            coords = line.split(',')
            if direction == '0.0':
                h_lines.append(float(coords[1]))
            else:
                v_lines.append(float(coords[0]))
        
        # Sort lines in ascending order
        h_lines.sort()
        v_lines.sort()
        
        # Create grid of rectangles
        n_rows = len(h_lines) - 1
        n_cols = len(v_lines) - 1
        rect_coords = np.zeros((n_rows, n_cols, 4))
        for i in range(n_rows):
            for j in range(n_cols):
                rect_coords[i,j] = [v_lines[j], h_lines[i], v_lines[j+1], h_lines[i+1]]
        
        # Save the coordinates of the rectangles to a text file
        with open(f'rect_coords_{page}.txt', 'w') as f:
            for i in range(n_rows):
                for j in range(n_cols):
                    f.write(','.join(str(coord) for coord in rect_coords[i,j]) + '\n')
      
      except:
           continue
      
      draw_tables(pdf)
      
def draw_tables(pdf):    

      doc = fitz.open(pdf)

      # Get the number of pages
      pages = doc.page_count

      for i in range(pages):

        try:

          page = doc[i]
          
          # Get the dimensions of the page
          page_width = page.rect.width
          page_height = page.rect.height
          
          # Open the text file containing the coordinates of the rectangles
          with open(f'rect_coords_{i}.txt', 'r') as f:
              lines = f.readlines()
          
          # Iterate over each line in the text file and draw the corresponding rectangle on the page
          for line in lines:
              # Split the line into its four coordinates
              x1, y1, x2, y2 = map(float, line.strip().split(','))
              # Transform coordinates per page size
              x1 = (x1*page_width)/899 
              x2 = (x2*page_width)/899
              y1 = (y1*page_height)/1000
              y2 = (y2*page_height)/1000
              
              # Calculate the dimensions of the rectangle
              rect_width = x2 - x1 
              rect_height = y2 - y1 

              # Draw the rectangle on the page
              rect = fitz.Rect(x1, y1, x1 + rect_width, y1 + rect_height)
              page.draw_rect(rect)
              
        except:
              continue
      # Save the PDF document to a file
      doc.save('output_annotated.pdf')
      doc.close()
