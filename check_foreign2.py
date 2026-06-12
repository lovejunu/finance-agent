import sys, io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")

import requests
from bs4 import BeautifulSoup
from briefing import NAVER_HEADERS, _parse_num

def scrape(sosok, type_):
    url = f"https://finance.naver.com/sise/sise_deal_rank_iframe.naver?sosok={sosok}&type={type_}"
    resp = requests.get(url, headers=NAVER_HEADERS, timeout=10)
    resp.encoding = "euc-kr"
    soup = BeautifulSoup(resp.text, "html.parser")
    items = []
    for tr in soup.select("tr"):
        tds = tr.select("td")
        if len(tds) < 3:
            continue
        name_a = tds[0].select_one("a")
        if not name_a:
            continue
        name = name_a.get_text(strip=True)
        if not name:
            continue
        amount = _parse_num(tds[2].get_text(strip=True))
        items.append((name, amount))
    return items[:5]

print("=== sosok=0 (KOSPI) 순매수 ===")
for n, a in scrape(0, "buy"):
    print(f"  {n}  {a:,.0f}백만")

print("=== sosok=1 (KOSDAQ) 순매수 ===")
for n, a in scrape(1, "buy"):
    print(f"  {n}  {a:,.0f}백만")

print("=== sosok=01 (현재 코드) 순매수 ===")
for n, a in scrape("01", "buy"):
    print(f"  {n}  {a:,.0f}백만")
