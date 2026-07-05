"""
GitHub Pages용 금융 대시보드 생성 — 시트(탭)별로 정보를 나눠 보여주는 정적 페이지.
briefing.py의 데이터 수집·카드 렌더링 함수를 그대로 재사용한다.
"""
import os
from datetime import datetime

from briefing import (
    KST, MARKET_GROUPS, BOND_ITEMS, NEWS_CATEGORIES,
    fetch, fetch_treasury_yields, fetch_categorized_news,
    fetch_nps_disclosures, fetch_naver_foreign,
    fmt_row, fmt_spread_row, build_market_card, build_news_card,
    build_nps_card, build_foreign_card, _key_metric_cell, _section_divider,
)

NEWS_TAB_ORDER = [
    ("연준 (Fed)",  "tab-fed",     "🏦", "연준"),
    ("국내정치",    "tab-kpol",    "🇰🇷", "국내정치"),
    ("해외정치",    "tab-fpol",    "🌐", "해외정치"),
    ("경제",        "tab-econ",    "💹", "경제"),
    ("군사·안보",   "tab-mil",     "🪖", "군사·안보"),
    ("경제 칼럼",   "tab-column",  "✍️", "칼럼"),
]


def build_tab_bar(tabs: list) -> str:
    buttons = "".join(
        f"<button class='tab-btn{' active' if i == 0 else ''}' data-tab='{tid}'>"
        f"<span class='tab-icon'>{icon}</span>{label}</button>"
        for i, (tid, label, icon, _html) in enumerate(tabs)
    )
    return f"<div class='tabbar-wrap'><div class='tabbar' id='tabbar'>{buttons}</div></div>"


def build_panels(tabs: list) -> str:
    panels = ""
    for i, (tid, _label, _icon, html) in enumerate(tabs):
        active = " active" if i == 0 else ""
        panels += f"<div class='tab-panel{active}' id='{tid}'>{html}</div>"
    return panels


def build_dashboard_html(tabs: list, now: datetime, key_metrics: dict) -> str:
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

    tabbar_html = build_tab_bar(tabs)
    panels_html = build_panels(tabs)

    return f"""<!DOCTYPE html>
<html lang="ko">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1,maximum-scale=1">
<title>글로벌 금융 대시보드</title>
<style>
  * {{ box-sizing:border-box; }}
  html {{ scroll-behavior:smooth; }}
  body {{
    margin:0;padding:0;background:#e2e8f0;
    font-family:-apple-system,BlinkMacSystemFont,'Apple SD Gothic Neo',
    'Noto Sans KR','Malgun Gothic',sans-serif;
  }}
  a {{ color:inherit; }}
  .wrap {{ max-width:760px;margin:0 auto;padding:14px; }}
  .hero {{
    background:linear-gradient(135deg,#0f172a 0%,#1e3a8a 60%,#1d4ed8 100%);
    color:#fff;padding:20px 20px 14px;border-radius:14px 14px 0 0;
  }}
  .tabbar-wrap {{
    position:sticky;top:0;z-index:10;background:#cbd5e1;
    border-radius:0 0 10px 10px;box-shadow:0 2px 6px rgba(0,0,0,.12);
    margin-bottom:10px;
  }}
  .tabbar {{
    display:flex;overflow-x:auto;gap:2px;padding:6px 6px 0;
    scrollbar-width:thin;
  }}
  .tabbar::-webkit-scrollbar {{ height:5px; }}
  .tabbar::-webkit-scrollbar-thumb {{ background:#94a3b8;border-radius:4px; }}
  .tab-btn {{
    flex:0 0 auto;border:none;cursor:pointer;white-space:nowrap;
    padding:9px 14px;font-size:12px;font-weight:700;color:#475569;
    background:#e2e8f0;border-radius:8px 8px 0 0;
    font-family:inherit;transition:background .15s,color .15s;
  }}
  .tab-btn .tab-icon {{ margin-right:5px; }}
  .tab-btn:hover {{ background:#f1f5f9;color:#1e293b; }}
  .tab-btn.active {{
    background:#fff;color:#1d4ed8;box-shadow:0 -2px 0 #1d4ed8 inset;
  }}
  .tab-panel {{ display:none; }}
  .tab-panel.active {{ display:block; }}
  @media(max-width:600px) {{
    .wrap {{ padding:8px !important; }}
    td {{ font-size:12px !important; }}
    .hero-title {{ font-size:17px !important; }}
    .tab-btn {{ padding:8px 11px;font-size:11px; }}
  }}
</style>
</head>
<body>
<div class="wrap">

  <div class="hero">
    <div style='font-size:10px;letter-spacing:2px;opacity:.5;text-transform:uppercase;margin-bottom:4px'>
      Daily Finance Dashboard
    </div>
    <div class="hero-title" style='font-size:20px;font-weight:800;letter-spacing:-0.5px'>
      📊 글로벌 금융 대시보드
    </div>
    <div style='font-size:11px;opacity:.6;margin-top:3px'>{date_str} 기준 자동 생성</div>
    {metrics_html}
  </div>

  {tabbar_html}

  {panels_html}

  <div style='text-align:center;padding:12px 0 6px;font-size:10px;color:#94a3b8;
              border-top:1px solid #e2e8f0;margin-top:6px'>
    자동 생성 · finance-agent &nbsp;|&nbsp;
    Yahoo Finance · Naver Finance · Treasury.gov · DART · RSS &nbsp;|&nbsp;
    매일 08:00 KST 갱신
  </div>
</div>

<script>
(function() {{
  var buttons = document.querySelectorAll('.tab-btn');
  var panels  = document.querySelectorAll('.tab-panel');

  function activate(tabId, updateHash) {{
    buttons.forEach(function(b) {{ b.classList.toggle('active', b.dataset.tab === tabId); }});
    panels.forEach(function(p) {{ p.classList.toggle('active', p.id === tabId); }});
    if (updateHash) history.replaceState(null, '', '#' + tabId);
  }}

  buttons.forEach(function(btn) {{
    btn.addEventListener('click', function() {{
      activate(btn.dataset.tab, true);
      btn.scrollIntoView({{ behavior: 'smooth', inline: 'center', block: 'nearest' }});
    }});
  }});

  var initial = (location.hash || '').replace('#', '');
  if (initial && document.getElementById(initial)) {{
    activate(initial, false);
  }}
}})();
</script>
</body>
</html>"""


def _find_news(cat_news: list, name: str) -> list:
    for category, _icon, items in cat_news:
        if category == name:
            return items
    return []


def main():
    now = datetime.now(KST)
    print(f"[{now.strftime('%H:%M:%S KST')}] 대시보드 생성 시작")

    # ① 시장 데이터
    print("  시장 데이터 수집 중...")
    market_data: dict[str, dict] = {}
    for _title, tickers in MARKET_GROUPS:
        for name, symbol in tickers.items():
            market_data[symbol] = fetch(symbol)

    # ② 채권
    print("  채권 데이터 수집 중 (Treasury.gov)...")
    tr_yields = fetch_treasury_yields()

    # ③ 외국인 순매수
    print("  네이버 금융 외국인 데이터 수집 중...")
    foreign_data = fetch_naver_foreign(5)

    # ④ 국민연금 공시
    print("  국민연금 DART 공시 수집 중...")
    nps_disc = fetch_nps_disclosures()

    # ⑤ 뉴스 (카테고리별)
    print("  뉴스 수집 및 번역 중...")
    cat_news = fetch_categorized_news(max_per=3)
    for category, _icon, items in cat_news:
        print(f"    [{category}] {len(items)}건")

    # ── 카드 조립 ──────────────────────────────────────────────────────────
    all_market_cards = ""
    for title, tickers in MARKET_GROUPS:
        rows = "".join(fmt_row(name, market_data[symbol], symbol) for name, symbol in tickers.items())
        all_market_cards += build_market_card(title, rows)

    bond_rows = ""
    bond_cache: dict[str, dict] = {}
    for name, key, is_yield in BOND_ITEMS:
        data = tr_yields.get(key, {"price": None, "change": None, "pct": None})
        bond_cache[key] = data
        bond_rows += fmt_row(name, data, key, is_yield=is_yield)
    d2, d10 = bond_cache.get("TR_2Y"), bond_cache.get("TR_10Y")
    if d2 and d2["price"] and d10 and d10["price"]:
        spread      = d10["price"] - d2["price"]
        prev_spread = (d10["price"] - d10["change"]) - (d2["price"] - d2["change"])
        bond_rows += fmt_spread_row(spread, prev_spread)
    else:
        bond_rows += fmt_spread_row(None, None)
    bonds_card = build_market_card("채권", bond_rows)

    foreign_card = build_foreign_card(foreign_data)
    nps_card     = build_nps_card(nps_disc)

    news_card_by_name = {
        name: build_news_card(name, icon, _find_news(cat_news, name))
        for name, _tid, icon, _label in NEWS_TAB_ORDER
    }
    all_news_html = "".join(news_card_by_name[name] for name, _tid, _icon, _label in NEWS_TAB_ORDER)

    # ── 시트(탭) 구성 ──────────────────────────────────────────────────────
    overview_html = (
        _section_divider("글로벌 시장")
        + all_market_cards + bonds_card
        + _section_divider("한국 투자 동향")
        + foreign_card + nps_card
        + _section_divider("오늘의 뉴스")
        + all_news_html
    )

    tabs = [
        ("tab-overview", "전체 정보",   "🗂️", overview_html),
        ("tab-indices",  "각종 지수",   "📈", all_market_cards + bonds_card),
        ("tab-nps",      "국민연금",    "🏛️", nps_card),
        ("tab-foreign",  "외국인 매매", "🏦", foreign_card),
    ]
    for name, tid, icon, label in NEWS_TAB_ORDER:
        tabs.append((tid, label, icon, news_card_by_name[name]))

    key_metrics = {
        "sp500":  market_data.get("^GSPC", {}),
        "kospi":  market_data.get("^KS11", {}),
        "usdkrw": market_data.get("KRW=X", {}),
        "t10y":   bond_cache.get("TR_10Y", {}),
    }

    html = build_dashboard_html(tabs, now, key_metrics)

    out_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "docs")
    os.makedirs(out_dir, exist_ok=True)
    out_path = os.path.join(out_dir, "index.html")
    with open(out_path, "w", encoding="utf-8") as f:
        f.write(html)
    print(f"[OK] 대시보드 생성 완료 → {out_path}")


if __name__ == "__main__":
    main()
