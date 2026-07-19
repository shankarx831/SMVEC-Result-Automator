import requests
import sys

def run_upload():
    session = requests.Session()
    
    # 1. Login
    login_url = "http://localhost:5001/login"
    data = {"username": "admin", "password": "admin123"}
    r = session.post(login_url, data=data)
    if "Invalid username or password" in r.text or r.status_code != 200:
        print("Login failed!")
        sys.exit(1)
        
    # 2. Upload file
    upload_url = "http://localhost:5001/generate"
    filepath = "/Users/shankar/Projects/Vanaja Mam/smvec-result-automator-old/DOB - III C .xlsx"
    files = {'file': open(filepath, 'rb')}
    data = {
        'url': 'http://exam.smvec.ac.in/exam_result_ug_pg_apr2026_regular/',
        'gen_excel': 'true',
        'gen_word': 'true'
    }
    print("Uploading file...")
    r = session.post(upload_url, files=files, data=data)
    print("Response status:", r.status_code)
    print(r.text[:500])

if __name__ == "__main__":
    run_upload()
