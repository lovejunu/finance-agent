import requests, json

headers = {"Accept": "application/json"}

# ECB FM 주요 금리 시리즈 테스트
ecb_series = {
    "ECB 예금수취금리(DFR)":  "https://data-api.ecb.europa.eu/service/data/FM/B.U2.EUR.4F.KR.DFR.LEV?lastNObservations=3&format=jsondata",
    "ECB 기준금리(MRR)":     "https://data-api.ecb.europa.eu/service/data/FM/B.U2.EUR.4F.KR.MRR_FR.LEV?lastNObservations=3&format=jsondata",
    "ECB YC 10Y":            "https://data-api.ecb.europa.eu/service/data/YC/B.U2.EUR.4F.G_N_A.SV_C_YM.SR_10Y?lastNObservations=3&format=jsondata",
    "ECB YC 2Y":             "https://data-api.ecb.europa.eu/service/data/YC/B.U2.EUR.4F.G_N_A.SV_C_YM.SR_2Y?lastNObservations=3&format=jsondata",
    "ECB YC 5Y":             "https://data-api.ecb.europa.eu/service/data/YC/B.U2.EUR.4F.G_N_A.SV_C_YM.SR_5Y?lastNObservations=3&format=jsondata",
    "ECB YC 30Y":            "https://data-api.ecb.europa.eu/service/data/YC/B.U2.EUR.4F.G_N_A.SV_C_YM.SR_30Y?lastNObservations=3&format=jsondata",
}

for name, url in ecb_series.items():
    try:
        r = requests.get(url, headers=headers, timeout=10)
        if r.status_code == 200:
            data = r.json()
            series = data["dataSets"][0]["series"]
            key = list(series.keys())[0]
            obs = series[key]["observations"]
            dates = data["structure"]["dimensions"]["observation"][0]["values"]
            last = sorted(obs.items(), key=lambda x: int(x[0]))[-1]
            idx, val = int(last[0]), last[1][0]
            d = dates[idx]["id"] if idx < len(dates) else last[0]
            print(f"  OK  {name:<28} {d}: {val:.4f}%")
        else:
            print(f"  ERR {name:<28} status={r.status_code}")
    except Exception as e:
        print(f"  EXC {name:<28} {e}")
