import requests
from bs4 import BeautifulSoup
import urllib3
urllib3.disable_warnings()

headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)'}

url = 'https://gunepribatua.atgipuzkoa.eus:8453/login/es'
try:
    print(f"Connecting to {url}...")
    r = requests.get(url, headers=headers, verify=False, timeout=12)
    print('Status code:', r.status_code)
    soup = BeautifulSoup(r.text, 'html.parser')
    print('Title:', soup.title.string.strip() if soup.title else 'No title')
    
    forms = soup.find_all('form')
    print('Forms found:', len(forms))
    for i, f in enumerate(forms):
        print(f"Form {i}: action={f.get('action')} method={f.get('method')}")
        for inp in f.find_all(['input', 'button', 'select']):
            print(f"  Field: name={inp.get('name')} type={inp.get('type')} id={inp.get('id')} placeholder={inp.get('placeholder')}")
            
    # Also inspect any labels or inputs across the page
    for lbl in soup.find_all('label'):
        print("Label:", lbl.get_text(strip=True))

except Exception as e:
    print('Error connecting to gunepribatua:', e)
