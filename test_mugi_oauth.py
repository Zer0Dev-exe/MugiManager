import requests
from bs4 import BeautifulSoup
import urllib3
urllib3.disable_warnings()

headers = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36',
    'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
    'Referer': 'https://gunepribatua.atgipuzkoa.eus:8453/login/es'
}

session = requests.Session()
login_url = 'https://gunepribatua.atgipuzkoa.eus:8453/login/es'

print("Step 1: GET login page to obtain CSRF token...")
r_get = session.get(login_url, headers=headers, verify=False, timeout=12)
soup = BeautifulSoup(r_get.text, 'html.parser')

form = soup.find('form')
action = form.get('action') if form else '/es/oauth/login'
if not action.startswith('http'):
    action = f"https://gunepribatua.atgipuzkoa.eus:8453{action}"

csrf_input = form.find('input', {'name': '__RequestVerificationToken'}) if form else None
csrf_token = csrf_input.get('value') if csrf_input else ''

client_id_input = form.find('input', {'name': 'ClientID'}) if form else None
client_id = client_id_input.get('value', '') if client_id_input else ''

print(f"Action URL: {action}")
print(f"CSRF Token found: {bool(csrf_token)} (Length: {len(csrf_token)})")
print(f"ClientID: {client_id}")

# Test with dummy credentials to see the exact rejection / success response format
payload = {
    '__RequestVerificationToken': csrf_token,
    'ClientID': client_id,
    'Email': 'test.invalid@ejemplo.eus',
    'Password': 'WrongPassword123'
}

print("Step 2: POST credentials to MUGI OAuth...")
r_post = session.post(action, data=payload, headers=headers, verify=False, timeout=12, allow_redirects=True)
print(f"POST Response: {r_post.status_code}")
print(f"Final URL: {r_post.url}")

post_soup = BeautifulSoup(r_post.text, 'html.parser')
# Check validation errors
errors = post_soup.select('.validation-summary-errors, .field-validation-error, .alert-danger, .error-message')
print("Errors found in response:", [e.get_text(strip=True) for e in errors])
for p in post_soup.find_all(['p', 'span', 'div', 'li']):
    txt = p.get_text(strip=True)
    if any(k in txt.lower() for k in ['incorrecto', 'contraseña', 'error', 'usuario']):
        if len(txt) < 120:
            print("Notice:", txt)
