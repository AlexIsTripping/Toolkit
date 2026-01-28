import fitz  # PyMuPDF
import xml.etree.ElementTree as ET
import re
import difflib
import textwrap
from pathlib import Path

# --- EXTRACTION LOGIC ---

def clean_text(text):
    if not text: return ""
    return re.sub(r'\s+', ' ', text).strip()

def split_into_sentences(text):
    sentences = re.split(r'(?<=[.!?]) +', text)
    return [s.strip() for s in sentences if len(s.strip()) > 2]

def extract_pdf_text(pdf_path):
    text = ""
    with fitz.open(str(pdf_path)) as doc:
        for page in doc:
            text += page.get_text()
    return clean_text(text)

def extract_xml_text(xml_path):
    tree = ET.parse(xml_path)
    root = tree.getroot()
    content_tags = {'article-title', 'book-title', 'subtitle', 'p', 'title', 'label', 'td', 'term', 'def'}
    extracted_parts = []
    for elem in root.iter():
        if elem.tag in content_tags:
            if elem.text and elem.text.strip():
                extracted_parts.append(elem.text.strip())
            if elem.tail and elem.tail.strip():
                extracted_parts.append(elem.tail.strip())
    return clean_text(" ".join(extracted_parts))

# --- FILE SELECTION UI (Symmetric Table) ---

def get_file_selection():
    base_dir = Path("files")
    if not base_dir.exists():
        base_dir.mkdir()
        print("|| Folder 'files' created. Please put your documents there and restart. ||")
        return None, None

    pdfs = list(base_dir.glob("*.pdf"))
    xmls = list(base_dir.glob("*.xml"))

    # Header
    print("\n" + "="*80)
    print("||" + " AVAILABLE DOCUMENTS IN /FILES/ ".center(76) + "||")
    print("="*80)
    
    # Column Headers (36 chars each + 4 chars for bars/space)
    print(f"|| {'[#] PDF DOCUMENTS':^36} || {'[#] XML DOCUMENTS':^36} ||")
    print("||" + "-"*38 + "||" + "-"*38 + "||")

    max_rows = max(len(pdfs), len(xmls))
    for i in range(max_rows):
        # Format strings to fit exactly 36 chars
        p_name = pdfs[i].name[:30] if i < len(pdfs) else ""
        x_name = xmls[i].name[:30] if i < len(xmls) else ""
        
        p_cell = f"[{i+1}] {p_name}" if p_name else ""
        x_cell = f"[{i+1}] {x_name}" if x_name else ""
        
        print(f"|| {p_cell:<36} || {x_cell:<36} ||")

    print("="*80)

    try:
        p_idx = int(input("Select PDF Number: ")) - 1
        x_idx = int(input("Select XML Number: ")) - 1
        return pdfs[p_idx], xmls[x_idx]
    except (ValueError, IndexError):
        print("|| Invalid selection. Try again. ||")
        return None, None

# --- UPDATED GRAPH SCANNER (NO RIGHT BARS) ---

def wrap_and_print(prefix, text, width=80):
    """Wraps text with a left bar only, no right-side bars."""
    wrapper = textwrap.TextWrapper(width=width)
    lines = wrapper.wrap(text=text)
    for i, line in enumerate(lines):
        if i == 0:
            print(f"|| {prefix} {line}")
        else:
            # Indent subsequent lines to line up with the start of the text
            indent = " " * len(prefix)
            print(f"|| {indent} {line}")

def draw_comparison_graph(pdf_sent, xml_sent):
    d = difflib.Differ()
    diff = list(d.compare(pdf_sent, xml_sent))
    
    # Header without right bars
    print("\n" + "="*80)
    print("|| DOCUMENT SCAN REPORT")
    print("="*80)
    
    line_num = 1
    for entry in diff:
        status = entry[0]
        sentence = entry[2:]
        
        if status == '  ': # Match
            if line_num % 15 == 0:
                print(f"|| Line {line_num:03} | [OK] Verified sequence matches...")
        
        elif status == '-': # PDF only
            print(f"||" + "-"*76)
            label = f"LINE {line_num:03} | MISSING IN XML:"
            wrap_and_print(label, sentence)
            print(f"||" + "-"*76)
            
        elif status == '+': # XML only
            print(f"||" + "+"*76)
            label = f"LINE {line_num:03} | EXTRA IN XML:  "
            wrap_and_print(label, sentence)
            print(f"||" + "+"*76)
            
        line_num += 1
    print("="*80 + "\n")

def main():
    pdf_file, xml_file = get_file_selection()
    
    if pdf_file and xml_file:
        print("\n" + "="*80)
        print(f"|| LOADING: {pdf_file.name[:30]:<30} VS {xml_file.name[:30]:<30} ||".center(80))
        print("="*80)
        
        pdf_text = extract_pdf_text(pdf_file)
        xml_text = extract_xml_text(xml_file)
        
        pdf_sentences = split_into_sentences(pdf_text)
        xml_sentences = split_into_sentences(xml_text)
        
        draw_comparison_graph(pdf_sentences, xml_sentences)

if __name__ == "__main__":
    main()