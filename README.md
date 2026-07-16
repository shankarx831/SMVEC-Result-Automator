# SMVEC Result Generation Automation

This project is a Python-based automation tool designed to fetch and compile exam results from the Sri Manakula Vinayagar Engineering College (SMVEC) exam portal automatically.

It reads student details (Registration Number and Date of Birth) from input Excel sheets, logs into the SMVEC portal by reading the text-based captcha, retrieves the results, and compiles them into Excel files and/or formatted Word documents with cropped screenshots.

## Features

- **Automated Login**: Uses Selenium to input registration numbers and dates of birth, automatically reading the text captcha directly from the portal's DOM.
- **Excel Compilation**: Writes fetched subject-wise grades and SGPAs back into Excel worksheets.
- **Word Document Reports**: Captures screenshots of the results, crops the active result panel, and generates a consolidated `.docx` document containing all student results for easy printing or record-keeping.
- **Error Handling**: Gracefully skips failed or missing entries and moves onto the next student record.

---

## Project Structure

- `app.py`: The main Flask web application starting script.
- `requirements.txt`: Python package dependencies.
- `data/`: Folder containing input student template sheets (e.g. `21-25 IT A.xlsx`).
- `templates/`: Flask HTML template files (e.g. `index.html`).
- `static/`: Static resources including custom preview images and compiled download assets.
- `archive/`: Legacy CLI automation scripts (`Generate.py`, `DocGenerate.py`, `test.py`).
- `Results/`: Directory where output results (Excel/Word files) are stored.

---

## Quick Start

1. **Clone the Repository**:
   ```bash
   git clone https://github.com/shankarx831/SMVEC-Result-Automator.git
   cd smvec-result-generation
   ```

2. **Run the Application**:
   Simply execute the application starter file:
   ```bash
   python app.py
   ```

   **What this does automatically:**
   - Detects and installs any missing libraries from `requirements.txt`.
   - Starts the local web server.
   - Automatically opens your default web browser and jumps to `http://127.0.0.1:5001`.

---

## How to Use the Web Dashboard

1. **Select / Upload Student Excel Sheet**:
   Select your Excel student list (e.g., `21-25 IT C.xlsx`). It should have:
   - Column A: Student Name
   - Column B: Registration Number (e.g., `21IT1001`)
   - Column C: Date of Birth (formatted as `DD.MM.YYYY`)

2. **Select Output Formats**:
   - Check **Excel Grades** to output parsed marks into a compiled spreadsheet.
   - Check **Word Report** to compile cropped portal result screenshots for each student.

3. **Click "Start Processing"**:
   - Headless Chrome will run in the background, automatically fill form inputs, read captchas, extract results, and compile download links.

---

*Made by **Sankara Narayanan.R (IT A 2025-2029)** with lot of Caffeine*


