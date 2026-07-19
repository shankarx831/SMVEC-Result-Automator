import os
import requests
from bs4 import BeautifulSoup
from PIL import Image, ImageDraw, ImageFont

def get_header_image():
    """Ensure the exact SMVEC 25-Year header logo is available locally."""
    img_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "static", "images")
    os.makedirs(img_dir, exist_ok=True)
    png_path = os.path.join(img_dir, "smvec_header.png")
    if os.path.exists(png_path):
        return png_path
    header_path = os.path.join(img_dir, "smvec_header.jpg")
    
    if not os.path.exists(header_path):
        try:
            img_url = "https://i0.wp.com/exam.smvec.ac.in/wp-content/uploads/2022/02/SMVCOELogo.jpg?fit=360%2C90&ssl=1"
            r = requests.get(img_url, headers={"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"}, timeout=5)
            if r.status_code == 200:
                with open(header_path, "wb") as f:
                    f.write(r.content)
            else:
                img = Image.new("RGB", (360, 90), color=(255, 255, 255))
                img.save(header_path)
        except Exception:
            img = Image.new("RGB", (360, 90), color=(255, 255, 255))
            img.save(header_path)
    return header_path

def get_font(size, bold=False):
    """Find a clean TrueType font across Mac/Linux platforms."""
    font_names = []
    if bold:
        font_names = [
            "/System/Library/Fonts/Supplemental/Arial Bold.ttf",
            "/Library/Fonts/Arial Bold.ttf",
            "/System/Library/Fonts/Helvetica.ttc",
            "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
            "/usr/share/fonts/truetype/liberation/LiberationSans-Bold.ttf"
        ]
    else:
        font_names = [
            "/System/Library/Fonts/Supplemental/Arial.ttf",
            "/Library/Fonts/Arial.ttf",
            "/System/Library/Fonts/Helvetica.ttc",
            "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
            "/usr/share/fonts/truetype/liberation/LiberationSans-Regular.ttf"
        ]
    
    for fn in font_names:
        if os.path.exists(fn):
            try:
                return ImageFont.truetype(fn, size)
            except Exception:
                pass
    return ImageFont.load_default()

def fetch_and_parse_result(session, portal_url, reg_no, dob_formatted, submit_btn_info=None):
    """
    Scrapes the SMVEC result portal using pure HTTP POST requests without Selenium/Chrome.
    Returns (rows, sgpa, student_name, meta_info, error_msg).
    """
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36",
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8",
        "Accept-Language": "en-US,en;q=0.9",
        "Connection": "keep-alive",
        "Referer": portal_url
    }
    
    if not submit_btn_info:
        r_get = session.get(portal_url, headers=headers, timeout=10)
        soup_get = BeautifulSoup(r_get.text, 'html.parser')
        submit_btn_info = {}
        for btn in soup_get.find_all(['button', 'input']):
            if btn.get('type') == 'submit' and btn.get('name'):
                submit_btn_info[btn.get('name')] = btn.get('value') or btn.text.strip() or "Get Result"
        if not submit_btn_info:
            submit_btn_info = {"ExamsResultUGPGAPR2026Regular": "Get Result", "ExamsResultUGMAYJUNE2024Regular": "Get Result"}

    payload = {
        "txtRollNo": reg_no,
        "txtDoB": dob_formatted,
        "txtcatcha": "abcdefg",
    }
    payload.update(submit_btn_info)

    r = session.post(portal_url, data=payload, headers=headers, timeout=12)
    soup = BeautifulSoup(r.text, 'html.parser')
    with open("actual_dump.html", "w") as f:
        f.write(soup.prettify())



    table = soup.find('table')
    if not table:
        text_lower = r.text.lower()
        if "no result found" in text_lower or "not found" in text_lower:
            return None, None, None, None, "No Result Found"
        if "mismatch" in text_lower or "try again" in text_lower:
            return None, None, None, None, "Captcha or Authentication Mismatch"
        return None, None, None, None, "Result table not found on page"

    full_text = soup.get_text(separator="\n")
    lines = [l.strip() for l in full_text.split("\n") if l.strip()]
    
    student_name = ""
    exam_title = "End Semester Examinations MAY/JUNE - 2024"
    branch = "B.TECH-Information Technology"
    announcement_date = "Result Announcement Date: 22/06/2024 & 05/07/2024 & 01/08/2024"
    
    for idx, line in enumerate(lines):
        if "End Semester Examinations" in line:
            exam_title = line
        if "B.TECH" in line or "B.E" in line or "M.TECH" in line or "M.B.A" in line or "M.C.A" in line:
            branch = line
        if "Result Announcement Date" in line:
            if ":" in line and len(line) > 25:
                announcement_date = line
            elif idx + 1 < len(lines):
                announcement_date = f"{line}: {lines[idx+1]}"
        if "Name of the Candidate" in line:
            if ":" in line:
                student_name = line.split(":")[-1].strip()
            elif idx + 1 < len(lines):
                student_name = lines[idx+1].strip()

    rows = []
    tr_list = table.find_all('tr')
    for tr in tr_list[1:]:
        cols = [td.text.strip() for td in tr.find_all(['td', 'th'])]
        if len(cols) >= 6:
            rows.append(cols[:6])
        elif len(cols) == 2:
            rows.append(['', '', cols[0], '', '', cols[1]])

    sgpa = ""
    for el in soup.find_all(string=lambda t: t and "SGPA" in t):
        parent_div = el.find_parent('div')
        if parent_div:
            sgpa_text = parent_div.get_text(separator=" ").strip()
            if ":" in sgpa_text:
                sgpa = sgpa_text.split(":")[-1].strip()
            else:
                # Fallback if no colon, just try to get the next sibling or text
                sgpa = sgpa_text.replace("SGPA", "").strip()
            if sgpa:
                break

    meta_info = {
        "exam_title": exam_title,
        "branch": branch,
        "announcement_date": announcement_date,
        "submit_btn_info": submit_btn_info
    }

    return rows, sgpa, student_name, meta_info, None

def draw_result_card(reg_no, name, meta_info, rows, sgpa, out_path):
    """
    Draws a 100% exact pixel replica of the SMVEC result portal card.
    Replicates exact border boxes, royal blue headers, gray scrollbar track, and font styling.
    """
    header_path = get_header_image()
    
    # Exact Geometry matching full-width 25-Year banner photo
    width = 980
    row_height = 36
    header_table_height = 42
    top_section_height = 370
    bottom_section_height = 55
    
    table_rows_height = len(rows) * row_height
    total_height = top_section_height + header_table_height + table_rows_height + bottom_section_height + 30
    
    img = Image.new("RGB", (width, total_height), "white")
    draw = ImageDraw.Draw(img)
    
    # Fonts
    f_title = get_font(21, bold=True)
    f_subtitle = get_font(16, bold=True)
    f_branch = get_font(17, bold=True)
    f_body_bold = get_font(14, bold=True)
    f_small_bold = get_font(13, bold=True)
    f_table_header = get_font(13, bold=True)
    f_table_row = get_font(13, bold=False)
    f_table_row_bold = get_font(13, bold=True)
    f_sgpa = get_font(16, bold=True)
    
    # 1. Outer Card Container Border
    draw.rectangle([15, 15, width - 15, total_height - 15], outline="#d1d5db", width=1)
    
    # 2. Paste Exact Header Banner Photo
    if os.path.exists(header_path):
        header_img = Image.open(header_path)
        w_h, h_h = header_img.size
        new_w = 880
        new_h = int(h_h * (new_w / w_h))
        header_img = header_img.resize((new_w, new_h), Image.Resampling.LANCZOS)
        img.paste(header_img, ((width - new_w) // 2, 28))
    
    # 3. Text Headers
    y = 185
    txt1 = "Office of the Controller of Examinations"
    w1 = draw.textlength(txt1, font=f_title)
    draw.text(((width - w1) // 2, y), txt1, fill="#112c80", font=f_title)
    
    y += 30
    txt2 = meta_info.get("exam_title", "End Semester Examinations MAY/JUNE - 2024")
    w2 = draw.textlength(txt2, font=f_subtitle)
    draw.text(((width - w2) // 2, y), txt2, fill="#112c80", font=f_subtitle)
    
    y += 28
    txt3 = meta_info.get("branch", "B.TECH-Information Technology")
    w3 = draw.textlength(txt3, font=f_branch)
    draw.text(((width - w3) // 2, y), txt3, fill="#000000", font=f_branch)
    
    # 4. Candidate Metadata Rows
    y += 38
    ann_text = meta_info.get("announcement_date", "Result Announcement Date: 22/06/2024 & 05/07/2024 & 01/08/2024")
    if ":" in ann_text:
        lbl, dt = ann_text.split(":", 1)
        lbl_str = f"{lbl.strip()}: "
        draw.text((34, y), lbl_str, fill="#ee3333", font=f_small_bold)
        w_lbl = draw.textlength(lbl_str, font=f_small_bold)
        draw.text((34 + int(w_lbl), y), dt.strip(), fill="#ee3333", font=f_small_bold)
    else:
        draw.text((34, y), ann_text, fill="#ee3333", font=f_small_bold)
    
    y += 26
    lbl_reg = "Register Number: "
    draw.text((34, y), lbl_reg, fill="#000000", font=f_body_bold)
    w_reg = draw.textlength(lbl_reg, font=f_body_bold)
    draw.text((34 + int(w_reg), y), str(reg_no), fill="#888888", font=f_body_bold)
    
    y += 26
    lbl_name = "Name of the Candidate: "
    draw.text((34, y), lbl_name, fill="#000000", font=f_body_bold)
    w_name = draw.textlength(lbl_name, font=f_body_bold)
    draw.text((34 + int(w_name), y), str(name), fill="#888888", font=f_body_bold)
    
    # 5. Table Layout
    y = top_section_height
    table_left = 34
    table_right = width - 34
    
    # Column widths: Sem (50), Subject Code (130), Subject Name (492), Point (65), Grade Point (95), Result (80)
    col_widths = [50, 130, 492, 65, 95, 80]
    col_x = [table_left]
    for w in col_widths:
        col_x.append(col_x[-1] + w)
    
    # Table Header Box (#0d2366)
    draw.rectangle([table_left, y, table_right, y + header_table_height], fill="#0d2366")
    
    # Draw vertical separator lines in header & row header labels
    headers = ["Sem", "Subject Code", "Subject Name", "Point", "Grade Point", "Result"]
    for i, h in enumerate(headers):
        if i > 0:
            draw.line([col_x[i], y, col_x[i], y + header_table_height], fill="#3a5298", width=1)
        
        # Text alignment
        if i in [0, 3, 4, 5]:
            tw = draw.textlength(h, font=f_table_header)
            tx = col_x[i] + (col_widths[i] - tw) // 2
        else:
            tx = col_x[i] + 12
        draw.text((tx, y + 12), h, fill="white", font=f_table_header)
    
    y += header_table_height
    
    # Table Rows
    for r_idx, row in enumerate(rows):
        row_top = y
        row_bottom = y + row_height
        
        draw.rectangle([table_left, row_top, table_right, row_bottom], fill="white")
        draw.line([table_left, row_bottom, table_right, row_bottom], fill="#e0e0e0", width=1)
        
        # Cell values and vertical grid lines
        for i, val in enumerate(row):
            if i >= len(col_widths): break
            if i > 0:
                draw.line([col_x[i], row_top, col_x[i], row_bottom], fill="#e0e0e0", width=1)
            
            val_str = str(val) if val is not None else ""
            
            if i == 5:
                fill_color = "#1ab340" if val_str.upper() == "PASS" else "#dc3545"
                cell_font = f_table_row_bold
            else:
                fill_color = "#444444"
                cell_font = f_table_row
                
            # Text alignment
            if i in [0, 3, 4, 5]:
                tw = draw.textlength(val_str, font=cell_font)
                tx = col_x[i] + (col_widths[i] - tw) // 2
            else:
                tx = col_x[i] + 12
            
            draw.text((tx, row_top + 10), val_str, fill=fill_color, font=cell_font)
        
        y += row_height
    
    # Outer box around entire table
    draw.rectangle([table_left, top_section_height, table_right, y], outline="#cccccc", width=1)
    
    # 6. SGPA Footer Row
    y += 18
    if sgpa:
        sgpa_str = f"SGPA: {sgpa}"
    else:
        sgpa_str = "SGPA:"
    sw = draw.textlength(sgpa_str, font=f_sgpa)
    tx_sgpa = table_right - sw - 5
    draw.text((tx_sgpa, y), sgpa_str, fill="#112c80", font=f_sgpa)
    
    img.save(out_path, "PNG")
    return out_path

if __name__ == "__main__":
    sample_rows = [
        ['6', 'U20HSO604', 'Open Elective III : Project Management for Engineers', '9', 'A', 'PASS'],
        ['6', 'U20ITC635', 'Certification Course VI : Data Science using R', '9', 'A', 'PASS'],
        ['6', 'U20ITE612', 'Professional Elective III : E-Commerce', '10', 'S', 'PASS'],
        ['6', 'U20ITM606', 'Essence of Indian Traditional Knowledge', '9', 'A', 'PASS'],
        ['6', 'U20ITP609', 'Artificial Intelligence Laboratory', '10', 'S', 'PASS'],
        ['6', 'U20ITP610', 'Data Science Laboratory', '10', 'S', 'PASS'],
        ['6', 'U20ITP611', 'Creative Innovative Project Laboratory', '9', 'A', 'PASS'],
        ['6', 'U20ITS606', 'Skill Development Course VI : Career and Professional Skill Development Program - II', '9', 'A', 'PASS'],
        ['6', 'U20ITS607', 'Skill Development Course VII : Technical Seminar', '10', 'S', 'PASS'],
        ['6', 'U20ITS608', 'Skill Development Course VIII : NPTEL / MOOC - I', '9', 'A', 'PASS'],
        ['6', 'U20ITT613', 'Artificial Intelligence', '8', 'B', 'PASS'],
        ['6', 'U20ITT614', 'Data Science and Analytics', '10', 'S', 'PASS'],
        ['6', 'U20ITT615', 'Design Thinking', '9', 'A', 'PASS'],
        ['6', 'U20ITT616', 'Block Chain Technology', '10', 'S', 'PASS']
    ]
    meta = {
        "exam_title": "End Semester Examinations MAY/JUNE - 2024",
        "branch": "B.TECH-Information Technology",
        "announcement_date": "Result Announcement Date: 22/06/2024 & 05/07/2024 & 01/08/2024"
    }
    draw_result_card("21UIT005", "AISWARYA SIVAPRASAD S", meta, sample_rows, "9.38", "exact_format_test.png")
