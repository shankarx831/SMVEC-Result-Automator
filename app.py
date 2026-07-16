import os
import sys
import subprocess

# Auto-install dependencies if any required libraries are missing
try:
    import flask
    import openpyxl
    import selenium
    import docx
    import PIL
except ImportError:
    print("Dependencies not met. Automatically installing required packages...")
    try:
        req_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'requirements.txt')
        if os.path.exists(req_path):
            subprocess.check_call([sys.executable, "-m", "pip", "install", "-r", req_path])
        else:
            subprocess.check_call([sys.executable, "-m", "pip", "install", "Flask", "openpyxl", "selenium", "python-docx", "pillow"])
        print("Dependencies successfully installed!")
    except Exception as e:
        print(f"Failed to automatically install dependencies: {e}")
        print("Please run: pip install -r requirements.txt manually.")
        sys.exit(1)

import time
import openpyxl
from flask import Flask, render_template, request, jsonify, send_from_directory
from werkzeug.utils import secure_filename
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from docx import Document
from docx.shared import Inches
from PIL import Image

app = Flask(__name__)
app.config['UPLOAD_FOLDER'] = os.path.join(app.root_path, 'uploads')
app.config['RESULTS_FOLDER'] = os.path.join(app.root_path, 'static', 'results')

# Ensure directories exist
os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)
os.makedirs(app.config['RESULTS_FOLDER'], exist_ok=True)

# Global status tracking variable
processing_status = "Idle"

def convert_date(date_str):
    if not date_str:
        return ""
    # Support formats like DD.MM.YYYY or DD/MM/YYYY or datetime objects
    date_str = str(date_str).strip()
    if "." in date_str:
        parts = date_str.split(".")
        if len(parts) == 3:
            return f"{parts[0]}/{parts[1]}/{parts[2]}"
    return date_str

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/status')
def status():
    return jsonify({"status": processing_status})

@app.route('/generate', methods=['POST'])
def generate():
    global processing_status
    if 'file' not in request.files:
        return jsonify({"error": "No file uploaded"}), 400
        
    file = request.files['file']
    if file.filename == '':
        return jsonify({"error": "No selected file"}), 400

    portal_url = request.form.get('url', 'http://exam.smvec.ac.in/exam_result_ug_pg_apr2026_regular/').strip()
    gen_excel = request.form.get('gen_excel') == 'true'
    gen_word = request.form.get('gen_word') == 'true'

    # Save uploaded template
    filename = secure_filename(file.filename)
    filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
    file.save(filepath)

    processing_status = "Loading Excel workbook..."
    try:
        workbook = openpyxl.load_workbook(filepath)
        worksheet = workbook.active
    except Exception as e:
        return jsonify({"error": f"Failed to read Excel file: {str(e)}"}), 400

    # Start browser setup
    processing_status = "Starting Headless Chrome..."
    chrome_options = Options()
    chrome_options.add_argument("--headless")
    chrome_options.add_argument("--no-sandbox")
    chrome_options.add_argument("--disable-dev-shm-usage")
    # For screenshotting correctly in headless
    chrome_options.add_argument("--window-size=1920,1080")

    driver = webdriver.Chrome(options=chrome_options)
    driver.get(portal_url)

    # Output filenames
    base_name = os.path.splitext(filename)[0]
    out_excel_name = f"{base_name}_Results.xlsx"
    out_word_name = f"{base_name}_Results.docx"
    out_excel_path = os.path.join(app.config['RESULTS_FOLDER'], out_excel_name)
    out_word_path = os.path.join(app.config['RESULTS_FOLDER'], out_word_name)

    doc = Document() if gen_word else None

    idx = 2
    num_rows = worksheet.max_row
    
    try:
        while idx <= num_rows:
            name = worksheet.cell(row=idx, column=1).value
            reg_no = worksheet.cell(row=idx, column=2).value
            dob = worksheet.cell(row=idx, column=3).value

            if not reg_no or not dob:
                idx += 1
                continue

            reg_no = str(reg_no).strip()
            dob_formatted = convert_date(dob)
            processing_status = f"Processing {idx-1}/{num_rows-1}: {name or ''} ({reg_no})"

            try:
                # 1. Wait for form elements
                wait = WebDriverWait(driver, 8)
                reg_input = wait.until(EC.presence_of_element_located((By.NAME, "txtRollNo")))
                dob_input = driver.find_element(By.NAME, "txtDoB")
                captcha_input = driver.find_element(By.NAME, "txtcatcha")

                # Locate the captcha text span (relative to captcha input)
                captcha_span = driver.find_element(By.XPATH, "//input[@name='txtcatcha']/../span[1]")
                captcha_val = captcha_span.text.strip()

                # Clear and send inputs
                reg_input.clear()
                reg_input.send_keys(reg_no)

                dob_input.clear()
                dob_input.send_keys(dob_formatted)

                captcha_input.clear()
                captcha_input.send_keys(captcha_val)

                # Find and click Submit button
                submit_btn = driver.find_element(By.XPATH, "//button[contains(text(), 'Get Result') or @type='submit']")
                submit_btn.click()

                # Wait for the results table to appear
                # The table contains student grades.
                results_table = wait.until(EC.presence_of_element_located((By.XPATH, "//table")))
                
                # Fetch SGPA text element
                # Typically inside the page body or specific div
                sgpa_element = wait.until(EC.presence_of_element_located((By.XPATH, "//*[contains(text(), 'SGPA')]")))
                sgpa_text = sgpa_element.text.strip()

                # 2. Extract grades if Excel option is selected
                if gen_excel:
                    result_data = {}
                    rows = results_table.find_elements(By.TAG_NAME, "tr")
                    for row in rows[1:]:
                        cols = row.find_elements(By.TAG_NAME, "td")
                        # Some tables have 6 columns (subject, marks, grade, etc.) or 2 columns
                        if len(cols) >= 2:
                            # Use content text based on layout
                            # Subject/Subject code is usually col 2 or col 0
                            # Grade/Marks is usually col 3 or col 1
                            if len(cols) == 6:
                                subject = cols[2].text.strip()
                                marks = cols[3].text.strip()
                            else:
                                subject = cols[0].text.strip()
                                marks = cols[1].text.strip()
                            if subject:
                                result_data[subject] = marks
                    
                    # Write to Excel sheet
                    col_mark = 4
                    for sub, grade in result_data.items():
                        # Set header name
                        worksheet.cell(row=1, column=col_mark).value = sub
                        worksheet.cell(row=idx, column=col_mark).value = grade
                        col_mark += 1
                    
                    # Set SGPA column
                    worksheet.cell(row=1, column=col_mark).value = "SGPA"
                    # Clean up SGPA label string if it contains "SGPA : 8.5"
                    sgpa_val = sgpa_text.split(":")[-1].strip() if ":" in sgpa_text else sgpa_text
                    worksheet.cell(row=idx, column=col_mark).value = sgpa_val

                # 3. Take screenshot and add to Word doc if selected
                if gen_word:
                    # Let's zoom to capture cleanly in headless mode
                    driver.execute_script("document.body.style.zoom='50%'")
                    time.sleep(1)
                    
                    temp_img_path = os.path.join(app.config['UPLOAD_FOLDER'], f"temp_{reg_no}.png")
                    
                    # Capture the parent division of results or entire page
                    try:
                        # Attempt to capture the results container
                        results_container = driver.find_element(By.XPATH, "//*[contains(@class, 'result') or @id='result'] | /html/body/div[3]/div[1]")
                        results_container.screenshot(temp_img_path)
                    except Exception:
                        # Fallback to full page screenshot
                        driver.save_screenshot(temp_img_path)
                    
                    # Crop image to focus on result panel if needed
                    # Or embed the screenshot directly
                    doc.add_heading(f'{reg_no} - {name or "Student"}', level=4)
                    doc.add_picture(temp_img_path, width=Inches(5.0))
                    doc.add_page_break()
                    
                    # Clean up temp image
                    if os.path.exists(temp_img_path):
                        os.remove(temp_img_path)
                        
                    driver.execute_script("document.body.style.zoom='100%'")

                # Reset the portal form for the next student
                reset_btn = driver.find_element(By.XPATH, "//button[contains(text(), 'Reset')]")
                reset_btn.click()
                time.sleep(1)

            except Exception as inner_err:
                print(f"Error processing record row {idx} ({reg_no}): {inner_err}")
                # Try navigating back or reloading url if page is stuck
                driver.get(portal_url)
                time.sleep(2)
                
            idx += 1

        # Save output assets
        if gen_excel:
            workbook.save(out_excel_path)
        if gen_word:
            doc.save(out_word_path)

    finally:
        driver.quit()
        processing_status = "Idle"

    return jsonify({
        "success": True,
        "excel_url": f"/download/{out_excel_name}" if gen_excel else None,
        "word_url": f"/download/{out_word_name}" if gen_word else None
    })

@app.route('/download_sample')
def download_sample():
    return send_from_directory(os.path.join(app.root_path, 'data'), '21-25 IT A.xlsx', as_attachment=True, download_name='sample_format.xlsx')

@app.route('/download/<filename>')
def download_file(filename):

    return send_from_directory(app.config['RESULTS_FOLDER'], filename, as_attachment=True)

if __name__ == '__main__':
    import webbrowser
    from threading import Timer

    def open_browser():
        webbrowser.open_new("http://127.0.0.1:5001")

    # Only open browser on the main thread, not on reloader threads
    if not os.environ.get("WERKZEUG_RUN_MAIN"):
        Timer(1.5, open_browser).start()

    app.run(host='0.0.0.0', port=5001, debug=True)
