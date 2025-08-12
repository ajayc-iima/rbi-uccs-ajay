import os
import re
import time
import requests
import pdfplumber
import xlsxwriter
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from webdriver_manager.chrome import ChromeDriverManager

# ---------------------------------------------------
# FILE AND DIRECTORY PATHS
# ---------------------------------------------------
try:
    # Assumes the script is in a 'src' folder, so goes one level up.
    BASE_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
except NameError:
    # Fallback for when __file__ is not defined (e.g., in an interactive session)
    BASE_DIR = os.getcwd()

DATA_DIR = os.path.join(BASE_DIR, "data")
RAW_DIR = os.path.join(DATA_DIR, "raw")
OUTPUT_DIR = os.path.join(DATA_DIR, "interim")

# ---------------------------------------------------
# PDF DOWNLOADING
# ---------------------------------------------------
def download_raw_pdfs():
    """
    Scrapes the RBI website for UCCS reports, downloading them into year-specific folders.
    """
    # Define and create year-specific save folders
    SAVE_FOLDER_2024 = os.path.join(RAW_DIR, "UCCS_Reports_2024")
    SAVE_FOLDER_2025 = os.path.join(RAW_DIR, "UCCS_Reports_2025")
    os.makedirs(SAVE_FOLDER_2024, exist_ok=True)
    os.makedirs(SAVE_FOLDER_2025, exist_ok=True)
    
    URL = "https://www.rbi.org.in/scripts/BimonthlyPublications.aspx?head=Urban%20Consumer%20Confidence%20Survey%20-%20Bi-monthly#"

    # --- Selenium WebDriver Setup ---
    print("Setting up web driver...")
    options = Options()
    for arg in ['--headless', '--no-sandbox', '--disable-dev-shm-usage', '--disable-gpu']:
        options.add_argument(arg)
    driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()), options=options)
    print("Driver setup complete.")

    def find_pdfs():
        """Finds all relevant PDF links on the current page."""
        links = driver.find_elements(By.CSS_SELECTOR, "a[href$='.PDF']")
        return [l.get_attribute('href') for l in links if l.get_attribute('href') and ('UCCS' in l.get_attribute('href').upper() or 'CCS' in l.get_attribute('href').upper())]

    def download_pdf(url, year):
        """Downloads a single PDF to the correct year-specific raw data folder."""
        target_folder = SAVE_FOLDER_2024 if year == 2024 else SAVE_FOLDER_2025
        path = os.path.join(target_folder, os.path.basename(url))
        
        if os.path.exists(path):
            print(f"'{os.path.basename(url)}' exists in '{os.path.basename(target_folder)}', skipping.")
            return True
        print(f"Downloading '{os.path.basename(url)}' to '{os.path.basename(target_folder)}'...")
        try:
            resp = requests.get(url); resp.raise_for_status()
            with open(path, 'wb') as f:
                f.write(resp.content)
            print("  Saved.")
            return True
        except Exception as e:
            print(f"  Failed: {e}")
            return False

    def collect_2024_pdfs():
        """Navigates the 2024 accordion menu to find all PDF links."""
        pdfs = []
        try:
            months_xpath = "//div[@id='2024']//a[contains(@onclick, 'GetYearMonth')]"
            WebDriverWait(driver, 15).until(EC.element_to_be_clickable((By.XPATH, "//div[contains(@class, 'accordionButton') and contains(., '2024')]"))).click()
            time.sleep(1)
            month_count = len(driver.find_elements(By.XPATH, months_xpath))

            for i in range(month_count):
                WebDriverWait(driver, 15).until(EC.element_to_be_clickable((By.XPATH, "//div[contains(@class, 'accordionButton') and contains(., '2024')]"))).click()
                time.sleep(1)
                month_link = driver.find_elements(By.XPATH, months_xpath)[i]
                print(f"Looking into '{month_link.text.strip()} 2024'...")
                driver.execute_script("arguments[0].click();", month_link)
                time.sleep(4)
                for pdf in find_pdfs():
                    print(f"  Found '{os.path.basename(pdf)}'")
                    pdfs.append(pdf)
            return list(set(pdfs))
        except Exception as e:
            print(f"Couldn't process 2024 tab, skipping. Reason: {e}")
            return []

    # --- Main Execution Logic for Downloading ---
    print(f"Navigating to RBI URL...")
    driver.get(URL)
    time.sleep(5)

    pdf_links_2025 = find_pdfs()
    print(f"Found {len(pdf_links_2025)} PDFs for the current year (2025).")
    pdf_links_2024 = collect_2024_pdfs()
    driver.quit()

    print("-" * 60)
    total_links = len(pdf_links_2025) + len(pdf_links_2024)
    print(f"Total unique PDFs found: {total_links}. Starting download...")
    
    downloaded_2025 = sum(download_pdf(link, 2025) for link in pdf_links_2025)
    downloaded_2024 = sum(download_pdf(link, 2024) for link in pdf_links_2024)
    total_downloaded = downloaded_2025 + downloaded_2024

    print(f"Finished downloading. Downloaded {total_downloaded} of {total_links} PDFs.")
    print("-" * 60)


# ---------------------------------------------------
# PDF PARSING AND EXCEL CONVERSION
# ---------------------------------------------------

def clean_sheet_name(name, existing_names):
    """Creates a valid and unique Excel sheet name."""
    clean = re.sub(r"[\[\]:*?/\\]", "", name).strip()[:31]
    if clean in existing_names:
        base_name, i = clean[:28], 1
        while f"{base_name}_{i}" in existing_names: i += 1
        clean = f"{base_name}_{i}"
    return clean

def process_table_panels(panels):
    """Cleans, merges, and structures raw table data from PDF panels."""
    junk_phrases = ["percentage responses", "applicable only for those respondents"]
    all_rows = [item for sublist in panels for item in sublist]
    
    string_rows = [
        [str(cell or "").strip() for cell in row] for row in all_rows 
        if any(str(c or "").strip() for c in row) and not any(jp in " ".join(map(str, row)).lower() for jp in junk_phrases)
    ]
    if not string_rows: return []

    header_rows, body_rows, header_ended = [], [], False
    for row in string_rows:
        is_data_row = bool(re.search(r'\b(?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)-\d{2}\b', ' '.join(row)))
        if is_data_row and not header_ended: header_ended = True
        (body_rows if header_ended else header_rows).append(row)
    if not body_rows: body_rows = [r for r in string_rows if r not in header_rows]

    body_rows = [row for row in body_rows if any(cell for cell in row[1:])]

    num_cols = max(len(r) for r in string_rows) if string_rows else 0
    merged_header = [""] * num_cols
    for r in header_rows:
        for i, cell in enumerate(r):
            if cell: merged_header[i] = f"{merged_header[i]} {cell}".strip()
    
    if body_rows and not merged_header[0] and re.search(r'\b(?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)-\d{2}\b', body_rows[0][0]):
        merged_header[0] = 'Survey Round'

    return [(merged_header, body_rows)]

def extract_pdf_data(pdf_path):
    """Extracts tables and their titles from a PDF, in order of appearance."""
    all_tables, current_title, current_panels = [], "Summary based on Net Responses", []
    with pdfplumber.open(pdf_path) as pdf:
        for page in pdf.pages:
            items = sorted(
                [("title", line['top'], line['text']) for line in page.extract_text_lines(layout=True, strip=True) if line['text'].lower().startswith("table ")] +
                [("table", table.bbox[1], table.extract()) for table in page.find_tables()],
                key=lambda x: x[1]
            )
            for item_type, _, data in items:
                if item_type == "title":
                    if current_panels: all_tables.append((current_title, current_panels))
                    current_title, current_panels = data, []
                else:
                    current_panels.append(data)
    if current_panels: all_tables.append((current_title, current_panels))
    return all_tables

def write_to_excel(tables_by_title, output_path):
    """Writes processed table data into a formatted Excel file."""
    with xlsxwriter.Workbook(output_path) as workbook:
        formats = {
            'title': workbook.add_format({'bold': True, 'font_size': 12, 'bottom': 1}),
            'header': workbook.add_format({'bold': True, 'bg_color': '#DDEBF7', 'border': 1, 'text_wrap': True, 'valign': 'vcenter'}),
            'cell': workbook.add_format({'border': 1, 'valign': 'top', 'text_wrap': True}),
            'num': workbook.add_format({'border': 1, 'valign': 'top', 'num_format': '0.0'})
        }
        sheet_names = []
        all_titles = [title for title, _ in tables_by_title]

        for title, panels in tables_by_title:
            sheet_name = clean_sheet_name(title, sheet_names)
            sheet_names.append(sheet_name)
            worksheet = workbook.add_worksheet(sheet_name)
            worksheet.merge_range(0, 0, 0, 10, title, formats['title'])
            current_row = 2

            for header, body in process_table_panels(panels):
                if not header and not body: continue
                
                cols_to_keep = [i for i, _ in enumerate(header) if any(i < len(row) and row[i].strip() for row in body)]
                if 0 not in cols_to_keep and header and header[0]: cols_to_keep.insert(0, 0)
                
                pruned_header = [header[i] for i in cols_to_keep]
                pruned_body = [[row[i] if i < len(row) else "" for i in cols_to_keep] for row in body]

                final_header = pruned_header
                if "perceptions and expectations" in title.lower() and len(pruned_header) == 9:
                    final_header = ['Survey Round', 'Current Perception -Increased', 'Current Perception-Remained Same', 'Current Perception-Decreased', 'Current Perception-Net Response', 'One year ahead Expectation- Will Increase', 'One year ahead Expectation-Will Remain Same', 'One year ahead Expectation-Will Decrease', 'One year ahead Expectation-Net Response']

                worksheet.write_row(current_row, 0, final_header, formats['header'])
                current_row += 1
                for row_data in pruned_body:
                    for col_num, cell in enumerate(row_data):
                        try: worksheet.write_number(current_row, col_num, float(cell), formats['num'])
                        except (ValueError, TypeError): worksheet.write_string(current_row, col_num, cell, formats['cell'])
                    current_row += 1
                
                for i, header_text in enumerate(final_header):
                    max_len = max([len(str(h)) for h in [header_text] + [r[i] for r in pruned_body if i < len(r)]])
                    worksheet.set_column(i, i, min(max_len + 3, 60))
        
        title_sheet = workbook.add_worksheet(clean_sheet_name("All Table Titles", sheet_names))
        title_sheet.write(0, 0, "All Table Titles (in PDF order)", formats['header'])
        for i, t in enumerate(all_titles, 1): title_sheet.write(i, 0, t, formats['cell'])
        title_sheet.set_column(0, 0, 80)

def parse_pdf_tables_to_excel():
    """Main function to find PDFs in year-specific raw data directories and convert them to Excel in corresponding interim directories."""
    print(f"Searching for PDF subdirectories in: {RAW_DIR}")
    
    try:
        # Process each subdirectory found in the raw folder (e.g., UCCS_Reports_2024)
        for sub_dir in os.listdir(RAW_DIR):
            raw_sub_dir_path = os.path.join(RAW_DIR, sub_dir)
            
            if os.path.isdir(raw_sub_dir_path):
                # Create corresponding output subdirectory
                output_sub_dir_path = os.path.join(OUTPUT_DIR, sub_dir)
                os.makedirs(output_sub_dir_path, exist_ok=True)
                
                pdf_files = [f for f in os.listdir(raw_sub_dir_path) if f.lower().endswith('.pdf')]
                if not pdf_files:
                    print(f"ℹ️ No PDF files found in '{raw_sub_dir_path}'. Skipping.")
                    continue

                print(f"✅ Found {len(pdf_files)} PDF(s) in '{sub_dir}'. Starting conversion...")
                for pdf_file in pdf_files:
                    pdf_path = os.path.join(raw_sub_dir_path, pdf_file)
                    output_path = os.path.join(output_sub_dir_path, os.path.splitext(pdf_file)[0] + '.xlsx')
                    print("-" * 60 + f"\nProcessing: '{pdf_file}'")
                    try:
                        tables = extract_pdf_data(pdf_path)
                        if not tables:
                            print(f"⚠️ No tables were found in '{pdf_file}'. Skipping.")
                            continue
                        write_to_excel(tables, output_path)
                        print(f"✅ Successfully created: '{os.path.join(sub_dir, os.path.basename(output_path))}'")
                    except Exception as e:
                        print(f"❌ An error occurred while processing '{pdf_file}': {e}")
                        import traceback
                        traceback.print_exc()
    except FileNotFoundError:
        print(f"❌ ERROR: The directory '{RAW_DIR}' was not found. Please run the download step first.")
        return
    print("-" * 60)


# ---------------------------------------------------
# MAIN EXECUTION BLOCK
# ---------------------------------------------------
if __name__ == "__main__":
    # Step 1: Download all the raw PDF files from the website into year-specific folders.
    download_raw_pdfs()
    
    # Step 2: Parse the downloaded PDFs from their folders and convert their tables to Excel files in corresponding folders.
    parse_pdf_tables_to_excel()

    print("\n✨ All processing complete.")
