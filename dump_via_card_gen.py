import requests
import card_generator

def dump_html():
    session = requests.Session()
    url = "http://exam.smvec.ac.in/exam_result_ug_pg_apr2026_regular/"
    reg = "22UIT003"
    dob = "09/05/2005"
    
    rows, sgpa, name, meta, err = card_generator.fetch_and_parse_result(session, url, reg, dob)
    print("SGPA:", repr(sgpa))
    print("Rows:", rows)

if __name__ == "__main__":
    dump_html()
