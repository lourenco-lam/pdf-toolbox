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

def extract_to_separate_pdfs(source_path, selected_pages, save_dir):
    """Extracts specific pages, saving each as its own PDF in a folder."""
    doc = fitz.open(source_path)
    base_name = os.path.splitext(os.path.basename(source_path))[0]
    
    for p in selected_pages:
        new_doc = fitz.open()
        new_doc.insert_pdf(doc, from_page=p, to_page=p)
        save_path = os.path.join(save_dir, f"{base_name}_page_{p+1}.pdf")
        new_doc.save(save_path)
        new_doc.close()
    doc.close()