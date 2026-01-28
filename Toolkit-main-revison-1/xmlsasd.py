import fitz  # PyMuPDF
import xml.etree.ElementTree as ET
import re
import textwrap
from pathlib import Path


# --- EXTRACTION ---
def find_func_path():
    def clean_text(text):
        if not text: return ""
        return re.sub(r'\s+', ' ', text).strip()

    def extract_pdf_paragraphs(pdf_path):
        paragraphs = []
        try:
            with fitz.open(str(pdf_path)) as doc:
                for page in doc:
                    blocks = page.get_text("blocks")
                    for b in blocks:
                        clean_p = clean_text(b[4])
                        # Filter out short fragments, page numbers, or empty strings
                        if len(clean_p) > 20: 
                            paragraphs.append(clean_p)
        except Exception as e:
            print(f"Error reading PDF: {e}")
        return paragraphs

    def extract_xml_paragraphs(xml_path):
        try:
            tree = ET.parse(xml_path)
            root = tree.getroot()
            content_tags = {'p', 'article-title', 'title', 'td', 'term', 'def', 'abstract'}
            extracted = []
            for elem in root.iter():
                if elem.tag in content_tags:
                    text = "".join(elem.itertext())
                    clean_p = clean_text(text)
                    if len(clean_p) > 20:
                        extracted.append(clean_p)
            return extracted
        except Exception as e:
            print(f"Error reading XML: {e}")
            return []

    # --- FIXED FORMATTING ENGINE ---

    def draw_table(pdf_paras, xml_pool, width=115):
        # Fixed Column Widths
        status_w = 12
        # Calculate content width: Total - status col - borders/spaces
        content_w = width - status_w - 9 
        
        border = "=" * width
        # Intersection line: ||-----------+------------||
        separator = "||" + "-" * (content_w + 2) + "+" + "-" * (status_w + 2) + "||"
        
        print("\n" + border)
        print(f"|| {'PDF CONTENT EXTRACT':<{content_w + 1}} | {'XML STATUS':<{status_w + 1}} ||")
        print(border)

        found_count = 0
        xml_pool_lower = [x.lower() for x in xml_pool]

        for para in pdf_paras:
            # Match logic: check if the first 60 chars of PDF para exist anywhere in XML
            match = any(para.lower()[:60] in x for x in xml_pool_lower)
            status_text = "FOUND" if match else "MISSING"
            if match: found_count += 1

            wrapper = textwrap.TextWrapper(width=content_w)
            lines = wrapper.wrap(text=para)

            for i, line in enumerate(lines):
                # Only show status on the first line of the wrapped paragraph block
                current_status = f"[{status_text}]" if i == 0 else ""
                # Fixed the formatting error by using status_w (int) instead of status_text (str)
                print(f"|| {line:<{content_w}} | {current_status:<{status_w + 1}} ||")
            
            print(separator)

        # Footer summary
        print(border)
        match_pct = (found_count / len(pdf_paras) * 100) if pdf_paras else 0
        summary = f"TOTAL MATCHES: {found_count}/{len(pdf_paras)} ({match_pct:.1f}%)"
        print(f"|| {summary:^{width - 6}} ||")
        print(border + "\n")

    # --- UI & MAIN ---

    def get_file_selection():
        base_dir = Path("files")
        if not base_dir.exists():
            base_dir.mkdir()
            print("|| Created /files/ directory. Add your files and restart. ||")
            return None, None
            
        pdfs = list(base_dir.glob("*.pdf"))
        xmls = list(base_dir.glob("*.xml"))
        
        if not pdfs or not xmls:
            print("!! Please drop at least one PDF and one XML in the /files/ folder !!")
            return None, None

        print(f"\n{'[#] PDF DOCUMENTS':<30} | {'[#] XML DOCUMENTS':<30}")
        print("-" * 65)
        for i in range(max(len(pdfs), len(xmls))):
            p = f"[{i+1}] {pdfs[i].name[:25]}" if i < len(pdfs) else ""
            x = f"[{i+1}] {xmls[i].name[:25]}" if i < len(xmls) else ""
            print(f"{p:<30} | {x:<30}")
        
        try:
            p_idx = int(input("\nSelect PDF Number: ")) - 1
            x_idx = int(input("Select XML Number: ")) - 1
            return pdfs[p_idx], xmls[x_idx]
        except (ValueError, IndexError):
            print("!! Invalid selection !!")
            return None, None
    pdf_path, xml_path = get_file_selection()
    if pdf_path and xml_path:
        print(f"\nScanning content blocks...")
        pdf_content = extract_pdf_paragraphs(pdf_path)
        xml_content = extract_xml_paragraphs(xml_path)
        
        if not pdf_content:
            print("No significant text blocks found in PDF.")
            return
            
        draw_table(pdf_content, xml_content)

#  make this
    
def main():
  find_func_path()
  
  
if __name__ == "__main__":
    main()