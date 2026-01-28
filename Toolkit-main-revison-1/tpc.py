import xml.etree.ElementTree as ET
from pathlib import Path
import os

# --- 1. AEM COLOR SCHEME ---
class Colors:
    HEADER = '\033[95m'
    BITS_BLUE = '\033[94m' # BITS specific
    JATS_GREEN = '\033[92m' # JATS specific
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

# --- 3. AEM WORD WRAPPER ---
def wrap_context(text, word_limit=15):
    words = text.split()
    if not words: return f"{Colors.RED}[No text content found]{Colors.RESET}"
    lines = [" ".join(words[i : i + word_limit]) for i in range(0, len(words), word_limit)]
    return "\n".join(lines)

# --- 4. THE REPORTING ENGINE ---
def print_aem_violation(tag, line, context, violation, fix, spec_ref):
    """Prints a vertical stack based on AEM Spec rules with double spacing."""
    sep = f"{Colors.CYAN}{'-' * 150}{Colors.RESET}"
    
    print(f"{Colors.BOLD}{Colors.CYAN}TAG / SPEC REFERENCE{Colors.RESET}")
    print(f"{tag} ({Colors.YELLOW}{spec_ref}{Colors.RESET})")
    print(sep)
    
    print(f"{Colors.BOLD}{Colors.CYAN}LINE{Colors.RESET}")
    print(line)
    print(sep)
    
    print(f"{Colors.BOLD}{Colors.CYAN}CONTEXT{Colors.RESET}")
    print(f"{wrap_context(context, 15)}") 
    print(sep)
    
    print(f"{Colors.BOLD}{Colors.RED}VIOLATION{Colors.RESET}")
    print(violation)
    print(sep)
    
    print(f"{Colors.BOLD}{Colors.BITS_BLUE}REQUIRED ACTION (PER SPEC){Colors.RESET}")
    print(fix)
    # Added an extra \n here to separate the stacked entries
    print(f"{Colors.RED}{'=' * 150}{Colors.RESET}\n\n")

# --- 5. AEM SPECIFICATION AUDIT LOGIC ---
def run_aem_audit(xml_path):
    try:
        tree = ET.parse(xml_path, parser=LineNumberingParser())
        root = tree.getroot()
    except Exception as e:
        print(f"{Colors.RED}XML ERROR: {e}{Colors.RESET}")
        return

    # Determine DTD Mode for Spec-specific rules
    filename = xml_path.name.upper()
    is_bits = "_BITS" in filename
    is_jats = "_JATS" in filename
    dtd_label = "BITS" if is_bits else "JATS" if is_jats else "UNKNOWN"

    print(f"\n{Colors.BOLD}{Colors.CYAN}{'=' * 80}")
    print(f"|| AEM SPEC AUDIT: {filename:^55} ||")
    print(f"|| DTD MODE: {dtd_label:^62} ||")
    print(f"{'=' * 80}{Colors.RESET}\n")

    violation_count = 0
    
    # Mapping tags to mandatory attributes per AEM Spec
    aem_rules = {
        'article': (['article-type'], "Article-type"),
        'article-id': (['pub-id-type'], "JATS: article-id"),
        'book-id': (['pub-id-type'], "BITS: book-id"),
        'contrib': (['contrib-type'], "Contributors"),
        'publisher-loc': ([], "Publisher"), # Logic handled below
        'table-wrap': (['id', 'position'], "Tables"),
        'fig': (['id', 'position'], "Figures"),
        'graphic': (['xlink:href'], "Figures"),
        'ext-link': (['xlink:href', 'ext-link-type'], "External References"),
        'disp-formula': (['id'], "Math Equations"),
        'inline-formula': (['id'], "Math Equations"),
    }

    for elem in root.iter():
        tag = elem.tag
        line = getattr(elem, "_start_line_number", "?")
        full_text = "".join(elem.itertext()).strip()

        # 1. Mandatory Attribute Check
        if tag in aem_rules:
            required_attrs, spec_name = aem_rules[tag]
            for attr in required_attrs:
                if attr not in elem.attrib:
                    violation_count += 1
                    print_aem_violation(tag, line, full_text, 
                        f"Missing mandatory attribute: '{attr}'", 
                        f"Add {attr} to follow {spec_name} guidelines.", spec_name)

        # 2. BITS Specific: Publisher Location Rule
        if is_bits and tag == "publisher":
            if not any(child.tag == "publisher-loc" for child in elem):
                violation_count += 1
                print_aem_violation(tag, line, full_text,
                    "Missing <publisher-loc>",
                    "Spec Rule: <publisher-loc> is mandatory in BITS. Use 'Washington DC' for gov-based if unknown.",
                    "Publisher")

        # 3. Emphasis Rule: Uniform Bold in Titles
        if tag in ["title", "article-title", "book-title"]:
            children = list(elem)
            if len(children) == 1 and children[0].tag == "bold":
                violation_count += 1
                print_aem_violation(tag, line, full_text,
                    "Uniform Bold Emphasis found in Title",
                    "Spec Rule: Remove uniform emphasis in titles unless it provides additional meaning.",
                    "Emphasis")

        # 4. Math Rule: IDs for Formulas
        if tag in ["disp-formula", "inline-formula"]:
            if 'id' not in elem.attrib:
                violation_count += 1
                print_aem_violation(tag, line, full_text,
                    "Math Equation missing ID",
                    "Spec Rule: 'id' is mandatory for linking to <xref> pointers.",
                    "Math Equations")

    # Final Summary Dashboard
    if violation_count == 0:
        print(f"{Colors.BOLD}{Colors.JATS_GREEN}{'+' + '-'*78 + '+'}")
        print(f"| {'AEM COMPLIANT: No rule violations found.':^76} |")
        print(f"{'+' + '-'*78 + '+'}{Colors.RESET}")
    else:
        color = Colors.RED if violation_count > 5 else Colors.YELLOW
        print(f"{Colors.BOLD}{color}{'+' + '-'*78 + '+'}")
        print(f"| {'AEM AUDIT COMPLETE: ' + str(violation_count) + ' issues identified.':^76} |")
        print(f"{'+' + '-'*78 + '+'}{Colors.RESET}")

# --- 6. FILE SELECTOR ---
def main():
    base_dir = Path("files")
    if not base_dir.exists(): base_dir.mkdir()
    
    xmls = list(base_dir.glob("*.xml"))
    if not xmls:
        print(f"{Colors.RED}Please put XML files in the /files/ folder.{Colors.RESET}")
        return

    print(f"\n{Colors.BOLD}{Colors.CYAN}--- AEM SPECIFICATION SELECTOR ---{Colors.RESET}")
    for i, f in enumerate(xmls):
        print(f"  {Colors.BOLD}[{i+1}]{Colors.RESET} {f.name}")
    
    try:
        choice_input = input(f"\n{Colors.BOLD}Select File # > {Colors.RESET}")
        choice = int(choice_input) - 1
        if 0 <= choice < len(xmls):
            run_aem_audit(xmls[choice])
        else:
            print(f"{Colors.RED}Invalid selection.{Colors.RESET}")
    except ValueError:
        print(f"{Colors.RED}Please enter a valid number.{Colors.RESET}")

if __name__ == "__main__":
    main()