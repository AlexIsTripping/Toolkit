import xml.etree.ElementTree as ET
from pathlib import Path
import os
import re
import fitz  # PyMuPDF: Install via 'pip install pymupdf'

# --- 1. AEM COLOR SCHEME ---
class Colors:
    HEADER = '\033[95m'
    BITS_BLUE = '\033[94m' 
    JATS_GREEN = '\033[92m' 
    CYAN = '\033[96m'
    YELLOW = '\033[93m'
    RED = '\033[91m'
    BOLD = '\033[1m'
    RESET = '\033[0m'

if os.name == 'nt':
    os.system('color')

# --- 2. LINE NUMBER PARSER ---
class LineNumberingParser(ET.XMLParser):
    def _start(self, *args, **kwargs):
        element = super(self.__class__, self)._start(*args, **kwargs)
        element._start_line_number = self.parser.CurrentLineNumber
        return element

# --- 3. FORMATTING & REPORTING HELPERS ---
def wrap_context(text, word_limit=12):
    words = text.split()
    if not words: return f"{Colors.RED}[No text content]{Colors.RESET}"
    return " ".join(words[:word_limit]) + "..."

def print_aem_violation(tag, line, context, violation, fix, spec_ref):
    sep = f"{Colors.CYAN}{'-' * 80}{Colors.RESET}"
    print(f"{Colors.BOLD}{Colors.CYAN}REF: {spec_ref} | TAG: {tag} | LINE: {line}{Colors.RESET}")
    print(f"{Colors.YELLOW}CONTEXT: {wrap_context(context)}{Colors.RESET}") 
    print(f"{Colors.RED}VIOLATION: {violation}{Colors.RESET}")
    print(f"{Colors.BITS_BLUE}FIX: {fix}{Colors.RESET}")
    print(sep)

# --- 4. PDF TEXT EXTRACTION ---
def extract_pdf_text(pdf_path):
    """Extracts raw text from PDF for comparison."""
    text = ""
    try:
        with fitz.open(pdf_path) as doc:
            for page in doc:
                text += page.get_text("text") + " "
        return re.sub(r'\s+', ' ', text).strip()
    except Exception as e:
        print(f"{Colors.RED}PDF Error: {e}{Colors.RESET}")
        return None

# --- 5. THE FILE FIXING ENGINE ---
def save_fixed_copy(tree, original_path):
    audited_dir = Path("files/audited")
    if not audited_dir.exists(): audited_dir.mkdir(parents=True)
    new_path = audited_dir / (original_path.stem + "_FIXED" + original_path.suffix)
    
    ET.register_namespace('xlink', "http://www.w3.org/1999/xlink")
    ET.register_namespace('mml', "http://www.w3.org/1998/Math/MathML")
    
    tree.write(new_path, encoding="utf-8", xml_declaration=True)
    print(f"\n{Colors.BOLD}{Colors.JATS_GREEN}✔ AUTO-FIX COMPLETE: {new_path}{Colors.RESET}\n")

# --- 6. CORE AUDIT LOGIC (The "Viewing" Rules) ---
def run_aem_fixer(xml_path, pdf_text=None):
    try:
        parser = LineNumberingParser()
        tree = ET.parse(xml_path, parser=parser)
        root = tree.getroot()
    except Exception as e:
        print(f"{Colors.RED}XML ERROR: {e}{Colors.RESET}"); return

    filename = xml_path.name.upper()
    is_bits = "_BITS" in filename
    violation_count = 0

    print(f"\n{Colors.BOLD}{Colors.CYAN}{'=' * 80}")
    print(f"|| AEM AUDIT & VIEWING STAGE: {filename:^36} ||")
    print(f"{'=' * 80}{Colors.RESET}\n")

    # FRONT MATTER CHECK (NCES SPECIFIC)
    article_meta = root.find(".//article-meta") or root.find(".//book-meta")
    if article_meta is not None:
        if article_meta.find("./article-id[@pub-id-type='nces']") is None:
            violation_count += 1
            new_id = ET.Element("article-id")
            new_id.set("pub-id-type", "nces")
            new_id.text = "2021-126"
            article_meta.insert(0, new_id)
            print_aem_violation("article-id", "FRONT", "N/A", "Missing NCES ID", "Inserted 2021-126", "Front Matter")

    # TREE ITERATION
    xml_full_text_list = []
    for elem in root.iter():
        tag = elem.tag
        line = getattr(elem, "_start_line_number", "?")
        full_text = "".join(elem.itertext()).strip()
        if full_text: xml_full_text_list.append(full_text)

        # RULE: Publisher Loc
        if tag == "publisher" and not any(c.tag == "publisher-loc" for c in elem):
            violation_count += 1
            new_loc = ET.Element("publisher-loc"); new_loc.text = "Washington DC"
            elem.append(new_loc)
            print_aem_violation(tag, line, full_text, "Missing Publisher Loc", "Added Washington DC", "Front Matter")

        # RULE: Uniform Bold in Titles
        if tag in ["title", "article-title"] and len(list(elem)) == 1 and list(elem)[0].tag == "bold":
            violation_count += 1
            child = list(elem)[0]
            elem.text = child.text; elem.remove(child)
            print_aem_violation(tag, line, full_text, "Uniform Bold Removal", "Stripped <bold> from title", "Emphasis")

        # RULE: PDF Hyphens/Spaces
        if elem.text:
            cleaned = re.sub(r'(\w)-\s+(\w)', r'\1\2', elem.text)
            if cleaned != elem.text:
                violation_count += 1
                elem.text = cleaned
                print_aem_violation(tag, line, full_text, "Soft-hyphen Artifact", "Merged broken word", "Text Clean")

        # AUDITOR NOTES (Manual Review Required)
        if tag == "alt-text" and "not available" in (elem.text or "").lower():
            print(f"{Colors.YELLOW}[NOTE] Line {line}: Check PDF for actual Alt-Text.{Colors.RESET}")

    # PDF TEXT COMPARISON (If PDF was selected)
    if pdf_text:
        xml_blob = " ".join(xml_full_text_list)
        # Look for a sample of the PDF text in the XML
        sample_phrases = re.findall(r'[^.!?]{40,80}[.!?]', pdf_text)
        mismatch_found = False
        for phrase in sample_phrases[:15]: 
            if phrase.strip() not in xml_blob:
                print(f"{Colors.RED}[TEXT MISMATCH] Missing from XML: {phrase.strip()}{Colors.RESET}")
                mismatch_found = True
        if not mismatch_found:
            print(f"{Colors.JATS_GREEN}✔ Text flow matches PDF samples.{Colors.RESET}")

    if violation_count > 0:
        save_fixed_copy(tree, xml_path)
    else:
        print(f"{Colors.BOLD}{Colors.JATS_GREEN}No violations found.{Colors.RESET}")

# --- 7. MAIN INTERFACE ---
def main():
    base_dir = Path("files")
    if not base_dir.exists(): base_dir.mkdir()
    
    xmls = list(base_dir.glob("*.xml"))
    pdfs = list(base_dir.glob("*.pdf"))

    print(f"\n{Colors.BOLD}{Colors.CYAN}--- AEM VIEWING & COMPARISON TOOL ---{Colors.RESET}")
    
    if not xmls:
        print(f"{Colors.RED}No XML files found in /files folder.{Colors.RESET}"); return

    print(f"\n{Colors.BOLD}XML FILES:{Colors.RESET}")
    for i, f in enumerate(xmls): print(f"  [{i+1}] {f.name}")
    
    print(f"\n{Colors.BOLD}PDF FILES (Optional Comparison):{Colors.RESET}")
    for i, f in enumerate(pdfs): print(f"  [{i+1}] {f.name}")
    print(f"  [0] Skip PDF Comparison")

    try:
        xml_choice = int(input(f"\nSelect XML # > ")) - 1
        pdf_choice = int(input(f"Select PDF # (or 0) > ")) - 1
        
        pdf_content = None
        if pdf_choice >= 0:
            print(f"{Colors.YELLOW}Reading PDF...{Colors.RESET}")
            pdf_content = extract_pdf_text(pdfs[pdf_choice])

        run_aem_fixer(xmls[xml_choice], pdf_content)
        
    except (ValueError, IndexError):
        print(f"{Colors.RED}Selection Error.{Colors.RESET}")

if __name__ == "__main__":
    main()