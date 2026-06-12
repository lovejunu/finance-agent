"""
글로벌 금융 시장 모닝 브리핑 - 매일 오전 자동 발송
"""

import os, smtplib
import yfinance as yf
import feedparser
import requests
from bs4 import BeautifulSoup
from datetime import datetime, timezone, timedelta
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from dotenv import load_dotenv

load_dotenv()

KST = timezone(timedelta(hours=9))

# ── 시장 데이터 그룹 ──────────────────────────────────────────────────────────
MARKET_GROUPS = [
    ("미국 지수", {
        "S&P 500":   "^GSPC",
        "NASDAQ":    "^IXIC",
        "Dow Jones": "^DJI",
    }),
    ("유럽 지수", {
        "DAX":      "^GDAXI",
        "FTSE 100": "^FTSE",
        "CAC 40":   "^FCHI",
    }),
    ("한국 지수", {
        "KOSPI":  "^KS11",
        "KOSDAQ": "^KQ11",
    }),
    ("미국 섹터 ETF", {
        "반도체 (SOXX)":  "SOXX",
        "기술주 (XLK)":   "XLK",
        "금융 (XLF)":     "XLF",
        "에너지 (XLE)":   "XLE",
        "소재 (XLB)":     "XLB",
        "헬스케어 (XLV)": "XLV",
        "산업 (XLI)":     "XLI",
    }),
    ("환율", {
        "USD/KRW": "KRW=X",
        "EUR/USD": "EURUSD=X",
        "USD/JPY": "JPY=X",
        "USD/CNY": "CNY=X",
    }),
    ("원자재", {
        "금 (Gold)":   "GC=F",
        "은 (Silver)": "SI=F",
        "WTI 원유":    "CL=F",
        "브렌트유":    "BZ=F",
        "천연가스":    "NG=F",
        "구리":        "HG=F",
    }),
]

# 채권 — US Treasury는 Treasury.gov로, 나머지는 yfinance
# BOND_ITEMS: (표시명, 키, is_yield)
#   키가 "TR_*"이면 fetch_treasury_yields() 결과 사용
BOND_ITEMS = [
    ("미 2년물",    "TR_2Y",  True),
    ("미 10년물",   "TR_10Y", True),
    ("미 30년물",   "TR_30Y", True),
]
SPREAD_KEYS = ("TR_2Y", "TR_10Y")  # 장단기 금리차 계산에 사용

# ── 뉴스 피드 (카테고리별) ────────────────────────────────────────────────────
NEWS_CATEGORIES = [
    ("연준 (Fed)", "🏦", [
        ("Federal Reserve",  "https://www.federalreserve.gov/feeds/press_all.xml"),
        ("MarketWatch Fed",  "https://feeds.marketwatch.com/marketwatch/fedspeaks/"),
        ("CNBC",             "https://search.cnbc.com/rs/search/combinedcms/view.xml?partnerId=wrss01&id=10000664"),
    ]),
    ("경제", "💹", [
        ("MarketWatch",      "https://feeds.marketwatch.com/marketwatch/topstories/"),
        ("CNBC Economy",     "https://www.cnbc.com/id/10001147/device/rss/rss.html"),
        ("Investing.com",    "https://www.investing.com/rss/news_25.rss"),
    ]),
    ("군사·안보", "🪖", [
        ("Defense News",     "https://www.defensenews.com/arc/outboundfeeds/rss/?outputType=xml"),
        ("Breaking Defense", "https://breakingdefense.com/feed/"),
        ("War on the Rocks", "https://warontherocks.com/feed/"),
    ]),
    ("정치", "🗳️", [
        ("Politico",         "https://www.politico.com/rss/politicopicks.xml"),
        ("The Hill",         "https://thehill.com/feed/"),
        ("AP Politics",      "https://rsshub.app/apnews/politics"),
    ]),
    ("경제 칼럼", "✍️", [
        ("Project Syndicate", "https://www.project-syndicate.org/rss"),
        ("한국경제 오피니언",   "https://www.hankyung.com/rss/opinion"),
    ]),
]

# ── 국민연금 주요 보유종목 ────────────────────────────────────────────────────
NPS_HOLDINGS = [
    ("삼성전자",        "005930", "~9.0%"),
    ("SK하이닉스",      "000660", "~8.5%"),
    ("LG에너지솔루션",  "373220", "~8.3%"),
    ("삼성바이오로직스", "207940", "~8.1%"),
    ("현대차",          "005380", "~8.2%"),
    ("POSCO홀딩스",     "005490", "~8.7%"),
    ("NAVER",           "035420", "~9.1%"),
    ("카카오",          "035720", "~7.4%"),
    ("KB금융",          "105560", "~9.3%"),
    ("신한지주",        "055550", "~9.5%"),
]

YIELD_SYMBOLS = {"^TNX", "^IRX", "^FVX", "^TYX", "TR_2Y", "TR_10Y", "TR_30Y"}
SECTION_ICONS = {
    "미국 지수":     "🇺🇸",
    "유럽 지수":     "🇪🇺",
    "한국 지수":     "🇰🇷",
    "미국 섹터 ETF": "📊",
    "환율":          "💱",
    "채권":          "📋",
    "원자재":        "🛢️",
}

NAVER_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/124.0.0.0 Safari/537.36"
    ),
    "Referer": "https://finance.naver.com/",
    "Accept-Language": "ko-KR,ko;q=0.9",
}

UP_COLOR   = "#e03131"
DOWN_COLOR = "#1971c2"
FLAT_COLOR = "#64748b"
UP_BG      = "#fff5f5"
DOWN_BG    = "#e7f5ff"
FLAT_BG    = "#f8fafc"


# ── 데이터 수집 ──────────────────────────────────────────────────────────────

def fetch(symbol: str) -> dict:
    ticker = yf.Ticker(symbol)
    # fast_info 우선: 전일 종가(previous_close) 기준으로 정확한 등락률 계산
    # history의 iloc[-2]는 공휴일/데이터 누락 시 잘못된 날짜와 비교될 수 있음
    try:
        fi    = ticker.fast_info
        price = float(fi.last_price)
        prev  = float(fi.previous_close)
        if price > 0 and prev > 0:
            change = price - prev
            return {"price": price, "change": change, "pct": change / prev * 100}
    except Exception:
        pass
    # fallback: history (공휴일 갭 발생 가능)
    hist = ticker.history(period="5d").dropna(subset=["Close"])
    if len(hist) < 2:
        return {"price": None, "change": None, "pct": None}
    prev   = float(hist["Close"].iloc[-2])
    curr   = float(hist["Close"].iloc[-1])
    change = curr - prev
    return {"price": curr, "change": change, "pct": change / prev * 100}


def _is_korean(text: str) -> bool:
    return any('가' <= c <= '힣' for c in text)


def translate_headline(text: str) -> str:
    if _is_korean(text):
        return text
    try:
        from deep_translator import GoogleTranslator
        result = GoogleTranslator(source="auto", target="ko").translate(text[:500])
        return result if result else text
    except Exception:
        return text


def _fmt_pub_time(entry) -> str:
    try:
        if getattr(entry, "published_parsed", None):
            pub_utc = datetime(*entry.published_parsed[:6], tzinfo=timezone.utc)
            return pub_utc.astimezone(KST).strftime("%m/%d %H:%M")
        if getattr(entry, "published", None):
            return str(entry.published)[:16]
    except Exception:
        pass
    return ""


def fetch_categorized_news(max_per: int = 3) -> list:
    results = []
    for category, icon, feeds in NEWS_CATEGORIES:
        items, seen = [], set()
        for source_name, url in feeds:
            if len(items) >= max_per:
                break
            try:
                feed = feedparser.parse(url)
                for entry in feed.entries:
                    if len(items) >= max_per:
                        break
                    title = entry.get("title", "").strip()
                    link  = entry.get("link", "#")
                    if not title or title in seen:
                        continue
                    seen.add(title)
                    ko_title = translate_headline(title)
                    items.append({
                        "title":    ko_title,
                        "en_title": title if ko_title != title else "",
                        "link":     link,
                        "source":   source_name,
                        "time":     _fmt_pub_time(entry),
                    })
            except Exception:
                continue
        results.append((category, icon, items))
    return results


def fetch_treasury_yields() -> dict:
    """Treasury.gov 일별 수익률 곡선 데이터 (US 2Y·10Y·30Y)"""
    from xml.etree import ElementTree as ET
    ns = {
        "atom": "http://www.w3.org/2005/Atom",
        "m":    "http://schemas.microsoft.com/ado/2007/08/dataservices/metadata",
        "d":    "http://schemas.microsoft.com/ado/2007/08/dataservices",
    }
    maturity_tags = {
        "TR_2Y":  "BC_2YEAR",
        "TR_10Y": "BC_10YEAR",
        "TR_30Y": "BC_30YEAR",
    }
    now = datetime.now(KST)
    for offset in (0, 1):  # 당월, 전월 순서로 시도
        dt  = now - timedelta(days=30 * offset)
        url = (
            "https://home.treasury.gov/resource-center/data-chart-center/"
            "interest-rates/pages/xml?data=daily_treasury_yield_curve"
            f"&field_tdr_date_value_month={dt.strftime('%Y%m')}"
        )
        try:
            r = requests.get(url, headers={"User-Agent": "Mozilla/5.0"}, timeout=15)
            if r.status_code != 200:
                continue
            root = ET.fromstring(r.content)
            entries = root.findall("atom:entry", ns)
            dated = []
            for entry in entries:
                props = entry.find(".//m:properties", ns)
                if props is None:
                    continue
                date_el = props.find("d:NEW_DATE", ns)
                if date_el is None or not date_el.text:
                    continue
                dated.append((date_el.text[:10], props))
            dated.sort(key=lambda x: x[0])
            if len(dated) < 2:
                continue
            _, today_p = dated[-1]
            _, prev_p  = dated[-2]
            result = {}
            for key, tag in maturity_tags.items():
                curr_el = today_p.find(f"d:{tag}", ns)
                prev_el = prev_p.find(f"d:{tag}", ns)
                if curr_el is None or not curr_el.text:
                    result[key] = {"price": None, "change": None, "pct": None}
                    continue
                curr = float(curr_el.text)
                prev = float(prev_el.text) if prev_el is not None and prev_el.text else curr
                chg  = curr - prev
                result[key] = {"price": curr, "change": chg, "pct": chg / prev * 100 if prev else 0}
            return result
        except Exception:
            continue
    return {k: {"price": None, "change": None, "pct": None} for k in maturity_tags}


def _fetch_nps_by_type(key: str, detail_ty: str, start: str, end: str) -> list:
    """단일 공시 타입에 대해 국민연금 지분공시를 페이지 순회 수집."""
    found, page = [], 1
    while True:
        try:
            resp = requests.get(
                "https://opendart.fss.or.kr/api/list.json",
                params={
                    "crtfc_key": key,
                    "pblntf_detail_ty": detail_ty,
                    "bgn_de": start, "end_de": end,
                    "page_no": page, "page_count": 100,
                    "sort": "date", "sort_mth": "desc",
                },
                timeout=10,
            )
            data = resp.json()
        except Exception:
            break
        if data.get("status") != "000":
            break
        for d in (data.get("list") or []):
            if "국민연금" in d.get("flr_nm", ""):
                found.append({
                    "corp":      d.get("corp_name", ""),
                    "corp_code": d.get("corp_code", ""),
                    "report":    d.get("report_nm", ""),
                    "date":      d.get("rcept_dt", ""),
                    "rcept_no":  d.get("rcept_no", ""),
                })
        total = int(data.get("total_count") or 0)
        if page * 100 >= total:
            break
        page += 1
    return found


def _fetch_elestock_for_nps(key: str, corp_code: str, start: str, end: str) -> dict:
    """elestock API로 국민연금 보유비율 변동 조회.
    rcept_no 매칭 우선, 실패 시 날짜 근접 매칭으로 fallback.
    반환: {"by_rcept": {rcept_no: entry}, "all": [entry, ...]}
    """
    try:
        r = requests.get(
            "https://opendart.fss.or.kr/api/elestock.json",
            params={"crtfc_key": key, "corp_code": corp_code,
                    "bgn_de": start, "end_de": end},
            timeout=10,
        )
        by_rcept, all_entries = {}, []
        for item in (r.json().get("list") or []):
            if "국민연금" not in item.get("repror", ""):
                continue
            after  = float(item.get("sp_stock_lmp_rate",      "0") or "0")
            change = float(item.get("sp_stock_lmp_irds_rate", "0") or "0")
            entry  = {
                "before": round(after - change, 2),
                "after":  after,
                "change": change,
                "date":   item.get("rcept_dt", "").replace("-", ""),
            }
            by_rcept[item.get("rcept_no", "")] = entry
            all_entries.append(entry)
        return {"by_rcept": by_rcept, "all": sorted(all_entries, key=lambda x: x["date"], reverse=True)}
    except Exception:
        return {"by_rcept": {}, "all": []}


def fetch_nps_disclosures() -> list:
    """국민연금공단 지분공시 수집 + elestock으로 보유비율 변동 데이터 병합.
    D001(대량보유) + D002(임원·주요주주)를 스레드로 병렬 조회.
    """
    key = os.environ.get("DART_API_KEY", "")
    if not key:
        return []
    try:
        from concurrent.futures import ThreadPoolExecutor, as_completed
        now   = datetime.now(KST)
        start = (now - timedelta(days=30)).strftime("%Y%m%d")
        end   = now.strftime("%Y%m%d")

        # ① 지분공시 목록 수집 (D001 + D002 병렬)
        with ThreadPoolExecutor(max_workers=2) as pool:
            futs = [pool.submit(_fetch_nps_by_type, key, ty, start, end)
                    for ty in ("D001", "D002")]
            results: list[dict] = []
            for f in futs:
                results.extend(f.result())

        results.sort(key=lambda x: x["date"], reverse=True)
        results = results[:8]

        # ② corp_code별 elestock 병렬 조회
        unique_corps = {r["corp_code"] for r in results if r.get("corp_code")}
        with ThreadPoolExecutor(max_workers=4) as pool:
            elestock_map = {
                cc: pool.submit(_fetch_elestock_for_nps, key, cc, start, end)
                for cc in unique_corps
            }
            elestock_map = {cc: f.result() for cc, f in elestock_map.items()}

        # ③ 보유비율 병합: rcept_no 정확 매칭 → 날짜 근접 fallback
        for r in results:
            edata    = elestock_map.get(r.get("corp_code"), {})
            own      = edata.get("by_rcept", {}).get(r["rcept_no"])
            if not own:
                entries = edata.get("all", [])
                if entries:
                    own = min(entries, key=lambda e: abs(int(e["date"]) - int(r["date"])))
            r["before"] = own.get("before") if own else None
            r["after"]  = own.get("after")  if own else None
            r["change"] = own.get("change") if own else None

        return results
    except Exception:
        return []


def _parse_num(text: str) -> float:
    cleaned = (
        text.strip()
        .replace(",", "").replace("+", "").replace("%", "")
        .replace("▲", "").replace("▼", "")
    )
    try:
        return float(cleaned)
    except ValueError:
        return 0.0


def _scrape_deal_rank(type_: str) -> list:
    url = (
        "https://finance.naver.com/sise/sise_deal_rank_iframe.naver"
        f"?sosok=01&type={type_}"
    )
    resp = requests.get(url, headers=NAVER_HEADERS, timeout=10)
    resp.raise_for_status()
    resp.encoding = "euc-kr"
    soup  = BeautifulSoup(resp.text, "html.parser")
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
        qty    = _parse_num(tds[1].get_text(strip=True))
        amount = _parse_num(tds[2].get_text(strip=True))
        items.append({"name": name, "qty": qty, "amount": amount})
    return items


def fetch_naver_foreign(top_n: int = 5) -> dict:
    try:
        buy_items  = _scrape_deal_rank("buy")[:top_n]
        sell_items = _scrape_deal_rank("sell")[:top_n]
        return {
            "buy":  buy_items,
            "sell": sell_items,
            "date": datetime.now(KST).strftime("%Y/%m/%d"),
        }
    except Exception:
        return {"buy": [], "sell": [], "date": ""}


# ── HTML 헬퍼 ─────────────────────────────────────────────────────────────────

def _dir(c: float) -> str:
    return "up" if c > 0 else ("down" if c < 0 else "flat")

def _color(d: str) -> str:
    return {"up": UP_COLOR, "down": DOWN_COLOR, "flat": FLAT_COLOR}[d]

def _bg(d: str) -> str:
    return {"up": UP_BG, "down": DOWN_BG, "flat": FLAT_BG}[d]

def _arrow(d: str) -> str:
    return {"up": "▲", "down": "▼", "flat": "–"}[d]


def fmt_row(name: str, data: dict, symbol: str = "", is_yield: bool = False) -> str:
    if data["price"] is None:
        return (
            f"<tr><td style='padding:8px 10px;font-size:13px'>{name}</td>"
            f"<td colspan='3' style='padding:8px 10px;color:#94a3b8;font-size:12px'>데이터 없음</td></tr>"
        )
    d    = _dir(data["change"])
    c    = _color(d)
    bg_c = _bg(d)
    ar   = _arrow(d)
    sign = "+" if data["change"] > 0 else ""

    if is_yield or symbol in YIELD_SYMBOLS:
        price_s  = f"{data['price']:.3f}%"
        change_s = f"{ar} {sign}{data['change']:.3f}pp"
        pct_s    = f"{sign}{data['pct']:.2f}%"
    else:
        price_s  = f"{data['price']:,.2f}"
        change_s = f"{ar} {sign}{data['change']:,.2f}"
        pct_s    = f"{sign}{data['pct']:.2f}%"

    badge = (
        f"<span style='display:inline-block;background:#fff;color:{c};"
        f"padding:2px 7px;border-radius:20px;font-size:11px;font-weight:700;"
        f"border:1px solid {c}'>{pct_s}</span>"
    )
    return (
        f"<tr style='background:{bg_c}'>"
        f"<td style='padding:8px 10px;font-size:13px;font-weight:500;color:#1e293b'>{name}</td>"
        f"<td style='padding:8px 10px;text-align:right;font-size:13px;font-family:monospace;color:#1e293b'>{price_s}</td>"
        f"<td style='padding:8px 10px;text-align:right;font-size:12px;color:{c}'>{change_s}</td>"
        f"<td style='padding:8px 10px;text-align:right'>{badge}</td>"
        f"</tr>"
    )


def fmt_spread_row(spread: float | None, prev_spread: float | None) -> str:
    if spread is None:
        return (
            "<tr><td style='padding:8px 10px;font-size:13px'>장단기 금리차 (10Y-2Y)</td>"
            "<td colspan='3' style='padding:8px 10px;color:#94a3b8;font-size:12px'>계산 불가</td></tr>"
        )
    change = (spread - prev_spread) if prev_spread is not None else 0.0
    d    = _dir(change)
    c    = _color(d)
    bg_c = _bg(d)
    ar   = _arrow(d)
    sign = "+" if change > 0 else ""

    if spread < 0:
        spread_color = DOWN_COLOR
        status_label = "⚠️ 역전"
    elif spread > 0.5:
        spread_color = "#16a34a"
        status_label = "정상"
    else:
        spread_color = "#94a3b8"
        status_label = "평탄"

    return (
        f"<tr style='background:{bg_c}'>"
        f"<td style='padding:8px 10px;font-size:13px;font-weight:500;color:#1e293b'>장단기 금리차 (10Y-2Y)</td>"
        f"<td style='padding:8px 10px;text-align:right;font-size:13px;font-family:monospace;"
        f"color:{spread_color};font-weight:700'>{spread:+.3f}%p</td>"
        f"<td style='padding:8px 10px;text-align:right;font-size:12px;color:{c}'>{ar} {sign}{change:.3f}pp</td>"
        f"<td style='padding:8px 10px;text-align:right;font-size:12px;color:{spread_color}'>{status_label}</td>"
        f"</tr>"
    )


def _card(header_bg: str, header_html: str, body_html: str, accent: str = "") -> str:
    left = f"border-left:3px solid {accent};" if accent else ""
    return f"""
<div style='margin:0 0 8px;border-radius:10px;overflow:hidden;border:1px solid #e2e8f0;{left}'>
  <div style='background:{header_bg};padding:9px 14px;border-bottom:1px solid #e2e8f0'>
    {header_html}
  </div>
  {body_html}
</div>"""


def _section_divider(label: str) -> str:
    return (
        "<table style='width:100%;border-collapse:collapse;margin:16px 0 6px'><tr>"
        f"<td style='font-size:10px;font-weight:700;color:#64748b;letter-spacing:1.5px;"
        f"text-transform:uppercase;white-space:nowrap;padding-right:10px'>{label}</td>"
        "<td style='border-top:1px solid #cbd5e1;width:100%'></td>"
        "</tr></table>"
    )


def _table_header() -> str:
    return (
        "<table style='width:100%;border-collapse:collapse;background:#fff'>"
        "<thead><tr style='background:#f8fafc'>"
        "<th style='padding:5px 10px;text-align:left;font-size:10px;color:#94a3b8;font-weight:600'>종목</th>"
        "<th style='padding:5px 10px;text-align:right;font-size:10px;color:#94a3b8;font-weight:600'>현재가</th>"
        "<th style='padding:5px 10px;text-align:right;font-size:10px;color:#94a3b8;font-weight:600'>변동</th>"
        "<th style='padding:5px 10px;text-align:right;font-size:10px;color:#94a3b8;font-weight:600'>등락률</th>"
        "</tr></thead>"
        "<tbody>"
    )


MARKET_ACCENT = {
    "미국 지수":     "#3b82f6",
    "유럽 지수":     "#8b5cf6",
    "한국 지수":     "#ef4444",
    "미국 섹터 ETF": "#0ea5e9",
    "환율":          "#f59e0b",
    "채권":          "#10b981",
    "원자재":        "#f97316",
}

def build_market_card(title: str, rows_html: str) -> str:
    icon   = SECTION_ICONS.get(title, "📈")
    accent = MARKET_ACCENT.get(title, "#3b82f6")
    header = f"<span style='font-size:13px;font-weight:700;color:#1e3a5f'>{icon} {title}</span>"
    body   = _table_header() + rows_html + "</tbody></table>"
    return _card("#f1f5f9", header, body, accent=accent)


def build_news_card(category: str, icon: str, items: list) -> str:
    is_column = (category == "경제 칼럼")
    hdr_color = "#7c3aed" if is_column else "#78350f"
    bg_color  = "#ede9fe" if is_column else "#fef9c3"
    prefix    = "경제 칼럼 — " if is_column else "주요뉴스 — "
    header    = f"<span style='font-size:13px;font-weight:700;color:{hdr_color}'>{icon} {prefix}{category}</span>"

    if not items:
        body = "<div style='padding:10px 14px;color:#94a3b8;font-size:12px;background:#fff'>수집된 뉴스 없음</div>"
        return _card(bg_color, header, body)

    nums    = ["①", "②", "③", "④", "⑤"]
    bar_clr = "#7c3aed" if is_column else "#b45309"
    rows    = ""
    for i, it in enumerate(items):
        link     = it["link"]
        title    = it["title"]
        en_title = it.get("en_title", "")
        source   = it["source"]
        t        = it["time"]
        num      = nums[i] if i < len(nums) else "·"
        en_line  = (
            f"<div style='font-size:10px;color:#94a3b8;margin-top:2px;line-height:1.4'>{en_title}</div>"
            if en_title else ""
        )
        rows += (
            f"<tr style='border-bottom:1px solid #f1f5f9'>"
            f"<td style='padding:10px 14px;border-left:3px solid {bar_clr}'>"
            f"<table style='width:100%;border-collapse:collapse'><tr>"
            f"<td style='width:18px;vertical-align:top;font-size:12px;color:{bar_clr};"
            f"font-weight:700;padding-right:6px;padding-top:1px'>{num}</td>"
            f"<td>"
            f"<a href='{link}' style='font-size:13px;color:#1e293b;text-decoration:none;"
            f"line-height:1.5;display:block;font-weight:500'>{title}</a>"
            f"{en_line}"
            f"<div style='margin-top:4px'>"
            f"<span style='font-size:10px;background:#e2e8f0;color:#475569;padding:1px 6px;"
            f"border-radius:3px;font-weight:500'>{source}</span>"
            f"<span style='font-size:10px;color:#94a3b8;margin-left:6px'>{t}</span>"
            f"</div>"
            f"</td></tr></table>"
            f"</td></tr>"
        )
    body = f"<table style='width:100%;border-collapse:collapse;background:#fff'><tbody>{rows}</tbody></table>"
    return _card(bg_color, header, body, accent=bar_clr)


def build_nps_card(disclosures: list) -> str:
    h_rows = ""
    for name, code, pct in NPS_HOLDINGS:
        naver_url = f"https://finance.naver.com/item/main.naver?code={code}"
        h_rows += (
            f"<tr style='border-bottom:1px solid #f1f5f9'>"
            f"<td style='padding:6px 10px;font-size:12px;font-weight:500'>"
            f"<a href='{naver_url}' style='color:#1e293b;text-decoration:none'>{name}</a>"
            f"</td>"
            f"<td style='padding:6px 10px;text-align:center;font-size:11px;color:#64748b'>{code}</td>"
            f"<td style='padding:6px 10px;text-align:right;font-size:12px;"
            f"color:#7c3aed;font-weight:600'>{pct}</td>"
            f"</tr>"
        )
    holdings_table = (
        "<table style='width:100%;border-collapse:collapse;background:#fff'>"
        "<thead><tr style='background:#f8fafc'>"
        "<th style='padding:5px 10px;text-align:left;font-size:10px;color:#94a3b8;font-weight:600'>종목명</th>"
        "<th style='padding:5px 10px;text-align:center;font-size:10px;color:#94a3b8;font-weight:600'>코드</th>"
        "<th style='padding:5px 10px;text-align:right;font-size:10px;color:#94a3b8;font-weight:600'>보유비중(추정)</th>"
        f"</tr></thead><tbody>{h_rows}</tbody></table>"
    )

    if disclosures:
        def _fmt_date(s: str) -> str:
            return f"{s[:4]}/{s[4:6]}/{s[6:]}" if len(s) == 8 else s

        dart_base = "https://dart.fss.or.kr/dsaf001/main.do?rcpNo="
        d_rows = ""
        for d in disclosures:
            corp      = d["corp"]
            rno       = d["rcept_no"]
            dt        = _fmt_date(d["date"])
            dart_link = f"{dart_base}{rno}"

            before = d.get("before")
            after  = d.get("after")
            change = d.get("change")

            if before is not None and after is not None and change is not None:
                chg_color  = UP_COLOR if change > 0 else (DOWN_COLOR if change < 0 else FLAT_COLOR)
                chg_arrow  = "▲" if change > 0 else ("▼" if change < 0 else "–")
                before_s   = f"{before:.2f}%"
                after_s    = f"{after:.2f}%"
                change_s   = f"{chg_arrow} {abs(change):.2f}%p"
                pct_cells  = (
                    f"<td style='padding:6px 10px;text-align:right;font-size:11px;color:#64748b'>{before_s}</td>"
                    f"<td style='padding:6px 10px;text-align:right;font-size:12px;font-weight:700;color:#1e293b'>"
                    f"<a href='{dart_link}' style='color:#1e293b;text-decoration:none'>{after_s}</a></td>"
                    f"<td style='padding:6px 10px;text-align:right;font-size:11px;font-weight:700;color:{chg_color}'>{change_s}</td>"
                )
            else:
                pct_cells = (
                    f"<td colspan='3' style='padding:6px 10px;text-align:center;font-size:11px;color:#94a3b8'>"
                    f"<a href='{dart_link}' style='color:#4c1d95;text-decoration:none'>공시 보기</a></td>"
                )

            d_rows += (
                f"<tr style='border-bottom:1px solid #f1f5f9'>"
                f"<td style='padding:6px 10px;font-size:12px;font-weight:500;color:#1e293b'>{corp}</td>"
                f"{pct_cells}"
                f"<td style='padding:6px 10px;text-align:right;font-size:11px;color:#94a3b8'>{dt}</td>"
                f"</tr>"
            )
        disc_html = (
            "<div style='background:#f8fafc;padding:8px 14px;border-top:1px solid #e2e8f0'>"
            "<span style='font-size:11px;font-weight:700;color:#4c1d95'>최근 국민연금 지분 변동 종목</span></div>"
            "<table style='width:100%;border-collapse:collapse;background:#fff'>"
            "<thead><tr style='background:#f8fafc'>"
            "<th style='padding:5px 10px;text-align:left;font-size:10px;color:#94a3b8;font-weight:600'>종목</th>"
            "<th style='padding:5px 10px;text-align:right;font-size:10px;color:#94a3b8;font-weight:600'>변동 전</th>"
            "<th style='padding:5px 10px;text-align:right;font-size:10px;color:#94a3b8;font-weight:600'>변동 후</th>"
            "<th style='padding:5px 10px;text-align:right;font-size:10px;color:#94a3b8;font-weight:600'>증감</th>"
            "<th style='padding:5px 10px;text-align:right;font-size:10px;color:#94a3b8;font-weight:600'>날짜</th>"
            f"</tr></thead><tbody>{d_rows}</tbody></table>"
        )
    else:
        dart_note = (
            "DART_API_KEY를 .env에 설정하면 최신 공시 자동 수집"
            if not os.environ.get("DART_API_KEY") else "최근 30일 국민연금 지분공시 없음"
        )
        disc_html = (
            f"<div style='padding:7px 14px;font-size:11px;color:#94a3b8;"
            f"background:#fff;border-top:1px solid #e2e8f0'>{dart_note}</div>"
        )

    note   = "<div style='padding:5px 14px 8px;font-size:10px;color:#94a3b8;background:#fff'>* 보유비중은 최근 분기 공시 기준 추정치입니다</div>"
    header = "<span style='font-size:13px;font-weight:700;color:#4c1d95'>🏛️ 국민연금 주요 보유종목</span>"
    return _card("#ede9fe", header, holdings_table + disc_html + note)


def build_foreign_card(data: dict) -> str:
    if not data["buy"] and not data["sell"]:
        return ""
    date_label = f" ({data['date']})" if data.get("date") else ""

    def side_rows(items: list, is_buy: bool) -> str:
        if not items:
            return "<tr><td colspan='3' style='padding:8px;color:#94a3b8;font-size:12px;text-align:center'>없음</td></tr>"
        c   = UP_COLOR if is_buy else DOWN_COLOR
        out = ""
        for item in items:
            amt     = abs(item["amount"])
            amt_str = f"{amt:,.0f}백만" if amt < 1_000_000 else f"{amt/1_000_000:.2f}조"
            out += (
                f"<tr style='border-bottom:1px solid #f1f5f9'>"
                f"<td style='padding:7px 8px;font-size:12px;font-weight:500;color:#1e293b'>{item['name']}</td>"
                f"<td style='padding:7px 8px;text-align:right;font-size:11px;color:{c};"
                f"font-family:monospace'>{amt_str}</td>"
                f"<td style='padding:7px 8px;text-align:right;font-size:11px;color:#64748b'>"
                f"{abs(item['qty']):,.0f}천주</td>"
                f"</tr>"
            )
        return out

    buy_rows  = side_rows(data["buy"],  True)
    sell_rows = side_rows(data["sell"], False)
    header    = (
        f"<span style='font-size:13px;font-weight:700;color:#4c1d95'>"
        f"🏦 외국인 순매수/순매도 KOSPI{date_label}</span>"
    )
    body = (
        "<table style='width:100%;border-collapse:collapse'><tr>"
        f"<td style='width:50%;vertical-align:top;border-right:1px solid #e2e8f0'>"
        f"<div style='background:{UP_BG};padding:5px 8px;border-bottom:1px solid #e2e8f0'>"
        f"<span style='font-size:11px;font-weight:700;color:{UP_COLOR}'>▲ 순매수  금액·수량</span></div>"
        f"<table style='width:100%;border-collapse:collapse;background:#fff'>"
        f"<tbody>{buy_rows}</tbody></table></td>"
        f"<td style='width:50%;vertical-align:top'>"
        f"<div style='background:{DOWN_BG};padding:5px 8px;border-bottom:1px solid #e2e8f0'>"
        f"<span style='font-size:11px;font-weight:700;color:{DOWN_COLOR}'>▼ 순매도  금액·수량</span></div>"
        f"<table style='width:100%;border-collapse:collapse;background:#fff'>"
        f"<tbody>{sell_rows}</tbody></table></td>"
        "</tr></table>"
    )
    return _card("#ede9fe", header, body)


def _key_metric_cell(label: str, data: dict, is_yield: bool = False) -> str:
    if not data or data.get("price") is None:
        return (
            f"<td style='padding:10px 6px 4px;text-align:center'>"
            f"<div style='font-size:9px;color:rgba(255,255,255,.45);text-transform:uppercase;"
            f"letter-spacing:.5px'>{label}</div>"
            f"<div style='font-size:13px;font-weight:800;color:#fff;margin:3px 0'>–</div>"
            f"<div style='font-size:10px;color:rgba(255,255,255,.35)'>N/A</div>"
            f"</td>"
        )
    price = data["price"]
    pct   = data.get("pct") or 0.0
    is_up = pct > 0
    clr   = "#fca5a5" if is_up else "#93c5fd"
    arrow = "▲" if is_up else ("▼" if pct < 0 else "–")
    if is_yield:
        price_s = f"{price:.2f}%"
    elif price >= 1000:
        price_s = f"{price:,.0f}"
    else:
        price_s = f"{price:,.2f}"
    return (
        f"<td style='padding:10px 6px 4px;text-align:center'>"
        f"<div style='font-size:9px;color:rgba(255,255,255,.45);text-transform:uppercase;"
        f"letter-spacing:.5px'>{label}</div>"
        f"<div style='font-size:13px;font-weight:800;color:#fff;margin:3px 0'>{price_s}</div>"
        f"<div style='font-size:10px;color:{clr}'>{arrow} {abs(pct):.2f}%</div>"
        f"</td>"
    )


def build_html(
    market_cards: str,
    bonds_card:   str,
    foreign_card: str,
    nps_card:     str,
    news_cards:   str,
    now:          datetime,
    key_metrics:  dict = None,
) -> str:
    date_str = now.strftime("%Y년 %m월 %d일 (%A) %H:%M KST")
    km = key_metrics or {}

    metrics_html = (
        "<table style='width:100%;border-collapse:collapse;"
        "border-top:1px solid rgba(255,255,255,.15);margin-top:14px'><tr>"
        + _key_metric_cell("S&P 500",  km.get("sp500",  {}))
        + _key_metric_cell("KOSPI",    km.get("kospi",  {}))
        + _key_metric_cell("USD/KRW",  km.get("usdkrw", {}))
        + _key_metric_cell("미 10년물", km.get("t10y",   {}), is_yield=True)
        + "</tr></table>"
    )

    return f"""<!DOCTYPE html>
<html lang="ko">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width,initial-scale=1,maximum-scale=1">
  <style>
    * {{ box-sizing:border-box; }}
    body {{ margin:0;padding:0;background:#e2e8f0;
           font-family:-apple-system,BlinkMacSystemFont,'Apple SD Gothic Neo',
           'Noto Sans KR','Malgun Gothic',sans-serif; }}
    a {{ color:inherit; }}
    @media(max-width:600px) {{
      .wrap {{ padding:8px !important; }}
      td {{ font-size:12px !important; }}
      .hero-title {{ font-size:17px !important; }}
    }}
  </style>
</head>
<body>
<div class="wrap" style='max-width:600px;margin:0 auto;padding:14px'>

  <!-- ── 헤더 ── -->
  <div style='background:linear-gradient(135deg,#0f172a 0%,#1e3a8a 60%,#1d4ed8 100%);
              color:#fff;padding:20px 20px 14px;border-radius:14px;margin-bottom:6px'>
    <div style='font-size:10px;letter-spacing:2px;opacity:.5;text-transform:uppercase;margin-bottom:4px'>
      Daily Morning Briefing
    </div>
    <div class="hero-title" style='font-size:20px;font-weight:800;letter-spacing:-0.5px'>
      📊 글로벌 금융 시장
    </div>
    <div style='font-size:11px;opacity:.6;margin-top:3px'>{date_str}</div>
    {metrics_html}
  </div>

  {_section_divider("글로벌 시장")}
  {market_cards}
  {bonds_card}

  {_section_divider("한국 투자 동향")}
  {foreign_card}
  {nps_card}

  {_section_divider("오늘의 뉴스")}
  {news_cards}

  <!-- ── 푸터 ── -->
  <div style='text-align:center;padding:12px 0 6px;font-size:10px;color:#94a3b8;
              border-top:1px solid #e2e8f0;margin-top:6px'>
    자동 생성 · finance-agent &nbsp;|&nbsp;
    Yahoo Finance · Naver Finance · Treasury.gov · DART · RSS
  </div>
</div>
</body>
</html>"""


# ── 검증 로직 ─────────────────────────────────────────────────────────────────

NA_THRESHOLD = 0.5  # 전체 데이터 항목 중 N/A 비율이 이 값 이상이면 차단


def validate_data(market_data: dict, tr_yields: dict, cat_news: list) -> list:
    errors = []

    # 1. N/A 항목 과다 체크 (시장 + 채권 합산)
    total, na_count, na_names = 0, 0, []
    for _, tickers in MARKET_GROUPS:
        for name, symbol in tickers.items():
            total += 1
            if market_data.get(symbol, {}).get("price") is None:
                na_count += 1
                na_names.append(name)
    for name, key, _ in BOND_ITEMS:
        total += 1
        if tr_yields.get(key, {}).get("price") is None:
            na_count += 1
            na_names.append(name)
    if total and na_count / total >= NA_THRESHOLD:
        errors.append(
            f"N/A 항목 과다: {na_count}/{total}개 ({na_count / total * 100:.0f}%) — "
            f"예: {', '.join(na_names[:5])}"
        )

    # 2. 가격 0값 감지
    zero_names = []
    for _, tickers in MARKET_GROUPS:
        for name, symbol in tickers.items():
            price = market_data.get(symbol, {}).get("price")
            if price is not None and price == 0:
                zero_names.append(name)
    if zero_names:
        errors.append(f"비정상 0값 데이터: {', '.join(zero_names)}")

    # 3. 전체 뉴스 0건
    if sum(len(items) for _, _, items in cat_news) == 0:
        errors.append("전체 뉴스 0건 — RSS 피드 수집 실패")

    return errors


def send_error_alert(errors: list, now: datetime):
    subject = f"[⚠️ 브리핑 오류] {now.strftime('%m/%d')} 데이터 검증 실패"
    li_html = "".join(
        f"<li style='margin:8px 0;font-size:14px;color:#1e293b'>{e}</li>"
        for e in errors
    )
    html = f"""<!DOCTYPE html>
<html lang="ko">
<head><meta charset="utf-8"></head>
<body style='font-family:-apple-system,BlinkMacSystemFont,"Noto Sans KR",sans-serif;
             background:#f8fafc;margin:0;padding:20px'>
<div style='max-width:560px;margin:0 auto;background:#fff;border-radius:12px;
            border:1px solid #e2e8f0;overflow:hidden'>
  <div style='background:#dc2626;padding:18px 20px'>
    <div style='font-size:18px;font-weight:800;color:#fff'>⚠️ 모닝 브리핑 발송 차단</div>
    <div style='font-size:12px;color:#fca5a5;margin-top:4px'>
      {now.strftime("%Y-%m-%d %H:%M KST")} — 데이터 검증 실패
    </div>
  </div>
  <div style='padding:20px'>
    <p style='font-size:13px;color:#475569;margin:0 0 12px'>
      아래 문제가 감지되어 브리핑 발송을 차단했습니다. 데이터 소스를 확인하세요.
    </p>
    <ul style='margin:0;padding-left:18px;list-style:disc'>{li_html}</ul>
    <div style='margin-top:16px;padding:12px;background:#fef2f2;border-radius:8px;
                border-left:4px solid #dc2626;font-size:12px;color:#7f1d1d'>
      finance-agent 로그를 확인하거나 수동으로 briefing.py를 재실행하세요.
    </div>
  </div>
</div>
</body>
</html>"""
    send_email(subject, html)
    print(f"[WARN] 검증 실패 — 오류 알림 발송 완료 ({len(errors)}건)")


# ── 이메일 발송 ───────────────────────────────────────────────────────────────

def send_email(subject: str, html: str):
    user      = os.environ["GMAIL_USER"]
    password  = os.environ["GMAIL_APP_PASSWORD"]
    recipient = os.environ.get("RECIPIENT_EMAIL", user)
    msg = MIMEMultipart("alternative")
    msg["Subject"] = subject
    msg["From"]    = user
    msg["To"]      = recipient
    msg.attach(MIMEText(html, "html", "utf-8"))
    with smtplib.SMTP("smtp.gmail.com", 587) as server:
        server.ehlo()
        server.starttls()
        server.login(user, password)
        server.sendmail(user, recipient, msg.as_string())
    print(f"[OK] 브리핑 발송 완료 → {recipient}")


# ── 메인 ─────────────────────────────────────────────────────────────────────

def main():
    now = datetime.now(KST)
    print(f"[{now.strftime('%H:%M:%S KST')}] 브리핑 시작")

    # ── 1단계: 데이터 수집 ────────────────────────────────────────────────────

    # ① 시장 데이터 (지수·ETF·환율·원자재) — dict로 먼저 모두 수집
    print("  시장 데이터 수집 중...")
    market_data: dict[str, dict] = {}
    for title, tickers in MARKET_GROUPS:
        for name, symbol in tickers.items():
            data = fetch(symbol)
            market_data[symbol] = data
            if data["price"]:
                print(f"    {name}: {data['price']:,.2f} ({data['pct']:+.2f}%)")
            else:
                print(f"    {name}: N/A")

    # ② 채권 (Treasury.gov)
    print("  채권 데이터 수집 중 (Treasury.gov)...")
    tr_yields = fetch_treasury_yields()
    for name, key, _ in BOND_ITEMS:
        data = tr_yields.get(key, {"price": None, "change": None, "pct": None})
        print(f"    {name}: {data['price']:.3f}%" if data["price"] else f"    {name}: N/A")

    # ③ 외국인 순매수
    print("  네이버 금융 외국인 데이터 수집 중...")
    foreign_data = fetch_naver_foreign(5)
    if foreign_data["buy"]:
        print(f"    순매수 상위: {', '.join(s['name'] for s in foreign_data['buy'][:3])}")
    else:
        print("    외국인 데이터 없음")

    # ④ 국민연금 공시
    print("  국민연금 DART 공시 수집 중...")
    nps_disc = fetch_nps_disclosures()
    print(f"    공시 {len(nps_disc)}건")

    # ⑤ 뉴스 수집
    print("  뉴스 수집 및 번역 중...")
    cat_news = fetch_categorized_news(max_per=3)
    for category, _, items in cat_news:
        print(f"    [{category}] {len(items)}건")

    # ── 2단계: 검증 — 실패 시 오류 알림 발송 후 종료 ─────────────────────────
    print("  데이터 검증 중...")
    errors = validate_data(market_data, tr_yields, cat_news)
    if errors:
        for e in errors:
            print(f"  [ERROR] {e}")
        send_error_alert(errors, now)
        return

    # ── 3단계: HTML 빌드 ──────────────────────────────────────────────────────
    all_market_cards = ""
    for title, tickers in MARKET_GROUPS:
        rows = "".join(
            fmt_row(name, market_data[symbol], symbol)
            for name, symbol in tickers.items()
        )
        all_market_cards += build_market_card(title, rows)

    bond_rows  = ""
    bond_cache: dict[str, dict] = {}
    for name, key, is_yield in BOND_ITEMS:
        data = tr_yields.get(key, {"price": None, "change": None, "pct": None})
        bond_cache[key] = data
        bond_rows += fmt_row(name, data, key, is_yield=is_yield)

    d2  = bond_cache.get("TR_2Y")
    d10 = bond_cache.get("TR_10Y")
    if d2 and d2["price"] and d10 and d10["price"]:
        spread      = d10["price"] - d2["price"]
        prev_spread = (d10["price"] - d10["change"]) - (d2["price"] - d2["change"])
        bond_rows += fmt_spread_row(spread, prev_spread)
        print(f"    장단기 금리차: {spread:+.3f}%p")
    else:
        bond_rows += fmt_spread_row(None, None)

    bonds_card      = build_market_card("채권", bond_rows)
    foreign_card    = build_foreign_card(foreign_data)
    nps_card        = build_nps_card(nps_disc)
    news_cards_html = "".join(
        build_news_card(category, icon, items)
        for category, icon, items in cat_news
    )

    # ── 4단계: 발송 ───────────────────────────────────────────────────────────
    key_metrics = {
        "sp500":  market_data.get("^GSPC", {}),
        "kospi":  market_data.get("^KS11", {}),
        "usdkrw": market_data.get("KRW=X", {}),
        "t10y":   bond_cache.get("TR_10Y", {}),
    }
    html    = build_html(all_market_cards, bonds_card, foreign_card, nps_card, news_cards_html, now, key_metrics)
    subject = f"[모닝 브리핑] {now.strftime('%m/%d')} 글로벌 금융 시장"
    send_email(subject, html)


if __name__ == "__main__":
    main()
