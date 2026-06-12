from briefing import _scrape_deal_rank

buy = _scrape_deal_rank("buy")[:5]
sell = _scrape_deal_rank("sell")[:5]
print("=== 외국인 순매수 ===")
for i, x in enumerate(buy):
    print(f"  {i+1}. {x['name']}  {x['amount']:,.0f}백만")
print("=== 외국인 순매도 ===")
for i, x in enumerate(sell):
    print(f"  {i+1}. {x['name']}  {x['amount']:,.0f}백만")
