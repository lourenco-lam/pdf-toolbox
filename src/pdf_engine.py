import fitz
import os

def merge_pdfs(file_paths, save_path):
    """Stitches multiple PDFs together into a single file."""
    merged_pdf = fitz.open()
    for path in file_paths:
        source_pdf = fitz.open(path)
        merged_pdf.insert_pdf(source_pdf)
        source_pdf.close()
    merged_pdf.save(save_path)
    merged_pdf.close()

def extract_to_single_pdf(source_path, selected_pages, save_path):
    """Extracts specific pages into a new single PDF."""
    doc = fitz.open(source_path)
    new_doc = fitz.open()
    for p in selected_pages:
        new_doc.insert_pdf(doc, from_page=p, to_page=p)
    new_doc.save(save_path)
    new_doc.close()
    doc.close()

def extract_to_separate_pdfs(input_path, pages, output_folder):
    import os
    import fitz # Assuming you use PyMuPDF (fitz)
    
    doc = fitz.open(input_path)
    # Get filename without extension
    base_name = os.path.splitext(os.path.basename(input_path))[0]
    
    for page_num in pages:
        new_doc = fitz.open()
        new_doc.insert_pdf(doc, from_page=page_num, to_page=page_num)
        
        # New naming convention: (filename)-number.pdf
        output_filename = f"{base_name}-{page_num + 1}.pdf"
        output_path = os.path.join(output_folder, output_filename)
        
        new_doc.save(output_path)
        new_doc.close()
    doc.close()