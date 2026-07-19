# SMVEC Result Generation Automation

This project is a high-performance Python web application designed to fetch, parse, and compile exam results from the Sri Manakula Vinayagar Engineering College (SMVEC) exam portal automatically at lightning speed.

It reads student details (Registration Number and Date of Birth) from input Excel sheets, logs into the SMVEC portal natively via HTTP requests, bypasses the text-based captcha, and retrieves results. It then outputs both structured Excel files and visually perfect `.docx` report cards mathematically drawn via Python.

## Features

- **Blazing Fast Performance**: Replaced old, heavy Selenium logic with pure, native Python `requests`. Processes an entire classroom (~70 students) in just **30 seconds**.
- **Ultra-Lightweight & Cloud Ready**: Runs on a fraction of the memory (~30MB) compared to browser-based solutions. Fits perfectly on free cloud hosting tiers like Render (512MB RAM, 0.1 CPU).
- **Pixel-Perfect Result Cards**: Instead of taking clunky browser screenshots, the app mathematically draws an exact 100% pixel replica of the SMVEC portal result card using `Pillow`, and attaches them to `.docx` files perfectly aligned without blank pages.
- **Excel Data Extraction**: Automatically parses subject grades, points, and SGPA into a compiled spreadsheet.
- **Secure Authentication System**: Built-in Admin dashboard with hashed passwords and SQLite history tracking to limit generation spam.

---

## Project Structure

- `app.py`: The main Flask web application starting script.
- `card_generator.py`: The core engine that runs HTTP requests, parses the portal HTML, and draws the result image templates using Pillow.
- `db.py`: SQLite database handler for the admin/user authentication and history tracking.
- `wsgi.py` & `Procfile`: Ready-to-go deployment configuration for Gunicorn on cloud platforms like Render.
- `data/`: Folder containing input student template sheets (e.g. `21-25 IT A.xlsx`).
- `templates/`: Flask HTML template files (e.g. `index.html`, `admin.html`).

---

## Local Development (Quick Start)

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
   - Detects and installs any missing libraries from `requirements.txt` into an isolated `venv`.
   - Starts the local web server.
   - Automatically opens your default web browser to `http://127.0.0.1:5001`.

---

## Cloud Deployment (Render)

This application is fully optimized for **Render's Free Tier**:
1. Connect your GitHub repository to Render.
2. Select **Web Service**.
3. Render will automatically detect the Python environment.
4. The start command will be automatically picked up from the `Procfile`: `gunicorn -w 1 --threads 4 wsgi:app`
5. *(Optional)* Add a `FLASK_SECRET_KEY` and `DEFAULT_ADMIN_PASSWORD` in the Render Environment Variables tab.
6. Click **Deploy**!

---

## How to Use the Web Dashboard

1. **Select / Upload Student Excel Sheet**:
   Select your Excel student list. It should have columns that contain headers like:
   - "Name"
   - "Register No"
   - "DOB" (formatted as `DD.MM.YYYY` or `DD/MM/YYYY`)

2. **Select Output Formats**:
   - Check **Excel Grades** to output parsed marks into a compiled spreadsheet.
   - Check **Word Report** to compile the perfectly drawn result cards for each student into a `.docx` file.

3. **Click "Start Processing"**:
   - Sit back as the server compiles everything in seconds!

---

*Made by **Sankara Narayanan.R (IT A 2025-2029)** with lot of Caffeine*
