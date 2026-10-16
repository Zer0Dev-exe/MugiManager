import urllib.request
import json

base = 'http://127.0.0.1:8000'

# 1. Scraped News
with urllib.request.urlopen(f'{base}/api/mugi/scraped-news') as resp:
    news_data = json.loads(resp.read().decode('utf-8'))
    print(f'Scraped News count: {news_data["count"]}')
    for n in news_data["news"][:2]:
        print(f'  - {n["title"][:60]} ({n["source"]})')

# 2. Scraped Tariffs
with urllib.request.urlopen(f'{base}/api/mugi/scraped-tariffs') as resp:
    tariffs_data = json.loads(resp.read().decode('utf-8'))
    print(f'Scraped Tariffs tables count: {len(tariffs_data["tariffs"])}')

# 3. HTML & CSS validation
with urllib.request.urlopen(f'{base}/') as resp:
    html = resp.read().decode('utf-8')
    assert 'mugi_style.css' in html, 'mugi_style.css missing'
    assert 'icon-card' in html, 'icon-card symbol missing'
    assert 'icon-globe' in html, 'icon-globe symbol missing'
    print('HTML & SVG validation: PASSED!')

# 4. CSS file check
with urllib.request.urlopen(f'{base}/static/css/mugi_style.css') as resp:
    css = resp.read().decode('utf-8')
    assert '--mugi-green' in css, '--mugi-green missing'
    assert '--mugi-cyan' in css, '--mugi-cyan missing'
    assert '.svg-icon' in css, '.svg-icon missing'
    print('CSS palette and SVG class validation: PASSED!')

print('ALL SCRAPING & STYLE CHECKS SUCCEEDED!')
