"""대시보드 미리보기 — mock 데이터로 docs/index.html 생성 후 브라우저로 확인"""
import dashboard


def mk(price, pct):
    change = price * pct / 100
    return {"price": price, "change": change, "pct": pct}


MARKET_MOCK = {
    "^GSPC": mk(5823.4, 0.82),  "^IXIC": mk(18921.0, 1.14),  "^DJI": mk(43150.0, 0.44),
    "^GDAXI": mk(22341.0, -0.31), "^FTSE": mk(8712.0, 0.12),  "^FCHI": mk(7821.0, -0.55),
    "^KS11": mk(2641.0, -0.77),  "^KQ11": mk(752.3, -1.21),
    "SOXX": mk(231.4, 1.52),  "XLK": mk(198.2, 0.93),  "XLF": mk(47.3, 0.21),
    "XLE": mk(82.1, -0.44),   "XLB": mk(89.6, 0.08),   "XLV": mk(142.0, -0.15),
    "XLI": mk(133.5, 0.31),
    "KRW=X": mk(1374.5, -0.22), "EURUSD=X": mk(1.0842, 0.31),
    "JPY=X": mk(144.21, -0.18), "CNY=X": mk(7.2341, 0.05),
    "GC=F": mk(3321.4, 0.44),  "SI=F": mk(33.21, -0.88),
    "CL=F": mk(71.34, -1.21),  "BZ=F": mk(75.11, -0.99),
    "NG=F": mk(2.143, 2.31),   "HG=F": mk(4.821, 0.71),
}

TR_MOCK = {
    "TR_2Y":  mk(4.421, -0.5),
    "TR_10Y": mk(4.512, 0.3),
    "TR_30Y": mk(4.721, 0.2),
}

FOREIGN_MOCK = {
    "buy":  [{"name": "삼성전자", "qty": 1234, "amount": 82000},
             {"name": "SK하이닉스", "qty": 521, "amount": 31000},
             {"name": "현대차", "qty": 312, "amount": 18000},
             {"name": "POSCO홀딩스", "qty": 211, "amount": 9200},
             {"name": "LG에너지솔루션", "qty": 88, "amount": 4100}],
    "sell": [{"name": "카카오", "qty": 980, "amount": 34000},
             {"name": "NAVER", "qty": 421, "amount": 28000},
             {"name": "삼성바이오", "qty": 55, "amount": 15000},
             {"name": "KB금융", "qty": 390, "amount": 12000},
             {"name": "신한지주", "qty": 510, "amount": 10000}],
    "date": "2026/07/05",
}

NPS_MOCK = [
    {"corp": "삼성전기", "report": "임원ㆍ주요주주특정증권등소유상황보고서", "date": "20260703", "rcept_no": "20260703000224",
     "before": 8.81, "after": 9.02, "change": 0.21},
    {"corp": "달바글로벌", "report": "주식등의대량보유상황보고서(약식)", "date": "20260702", "rcept_no": "20260702000221",
     "before": 6.55, "after": 6.10, "change": -0.45},
    {"corp": "한미약품", "report": "주식등의대량보유상황보고서(약식)", "date": "20260701", "rcept_no": "20260701001481",
     "before": None, "after": None, "change": None},
]

NEWS_MOCK = [
    ("연준 (Fed)", "🏦", [
        {"title": "파월 의장, 금리 인하 서두르지 않겠다고 발언", "en_title": "Fed Chair Powell says no rush to cut rates", "link": "#", "source": "Federal Reserve", "time": "07/05 08:00"},
        {"title": "연준 위원들, 인플레 목표 달성에 더 많은 증거 필요", "en_title": "Fed officials need more evidence on inflation", "link": "#", "source": "MarketWatch", "time": "07/04 22:30"},
        {"title": "FOMC 의사록 공개 예정, 시장 주시", "en_title": "FOMC minutes release awaited by markets", "link": "#", "source": "CNBC", "time": "07/04 20:00"},
    ]),
    ("국내정치", "🇰🇷", [
        {"title": "국회, 본회의서 추경 예산안 처리 놓고 여야 대치", "en_title": "", "link": "#", "source": "연합뉴스", "time": "07/05 07:00"},
        {"title": "여당, 하반기 개각설에 술렁", "en_title": "", "link": "#", "source": "한겨레", "time": "07/04 22:00"},
        {"title": "야당, 특검법 재발의 예고", "en_title": "", "link": "#", "source": "조선일보", "time": "07/04 19:00"},
    ]),
    ("해외정치", "🌐", [
        {"title": "미 의회, 대규모 인프라 예산안 통과", "en_title": "US Congress passes major infrastructure bill", "link": "#", "source": "Politico", "time": "07/05 06:00"},
        {"title": "G7 정상회의, 무역 정책 공조 논의", "en_title": "G7 summit discusses trade policy coordination", "link": "#", "source": "The Hill", "time": "07/04 21:00"},
    ]),
    ("경제", "💹", [
        {"title": "미국 CPI 예상치 하회, 인플레 둔화 신호", "en_title": "US CPI comes in below expectations", "link": "#", "source": "MarketWatch", "time": "07/05 09:00"},
        {"title": "중국 수출 급증, 글로벌 무역 긴장 고조", "en_title": "China exports surge, global trade tensions rise", "link": "#", "source": "CNBC Economy", "time": "07/04 18:00"},
    ]),
    ("군사·안보", "🪖", [
        {"title": "NATO 회원국들 방위비 증액 합의", "en_title": "NATO members agree to increase defense spending", "link": "#", "source": "Defense News", "time": "07/05 07:00"},
        {"title": "중동 지역 긴장 고조, 유가 영향", "en_title": "Middle East tensions escalate, oil prices react", "link": "#", "source": "Breaking Defense", "time": "07/04 16:00"},
    ]),
    ("경제 칼럼", "✍️", [
        {"title": "인공지능 시대의 노동 시장 재편: 누가 혜택을 받는가", "en_title": "Reshaping the Labor Market in the AI Era", "link": "#", "source": "Project Syndicate", "time": "07/05 05:00"},
        {"title": "금리 정상화 이후 부동산 시장의 미래", "en_title": "", "link": "#", "source": "한국경제 오피니언", "time": "07/04 23:00"},
    ]),
]

dashboard.fetch                  = lambda symbol: MARKET_MOCK[symbol]
dashboard.fetch_treasury_yields  = lambda: TR_MOCK
dashboard.fetch_naver_foreign    = lambda top_n=5: FOREIGN_MOCK
dashboard.fetch_nps_disclosures  = lambda: NPS_MOCK
dashboard.fetch_categorized_news = lambda max_per=3: NEWS_MOCK

dashboard.main()
