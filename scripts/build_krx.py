"""국내 KRX 데이터 수집. 사용법: python3 build_krx.py [YYYYMMDD]
.env의 KRX_ID, KRX_PW가 환경변수로 export 되어 있어야 한다.
결과: krx_ohlcv_{date}.json, krx_netbuy_{date}.json, krx_flow_{date}.json
"""
import os
import sys
import json
import pandas as pd
from pykrx import stock

WORK = os.path.dirname(os.path.abspath(__file__))
DATE = sys.argv[1] if len(sys.argv) > 1 else '20261023'

# 1) 전 종목 OHLCV (코스피 + 코스닥)
ohlcv = []
for mkt in ['KOSPI', 'KOSDAQ']:
    df = stock.get_market_ohlcv_by_ticker(DATE, market=mkt)
    df['시장'] = mkt
    ohlcv.append(df)
pd.concat(ohlcv).reset_index().to_json(f'{WORK}/krx_ohlcv_{DATE}.json', orient='records', force_ascii=False)

# 2) 종목별 외국인·기관 순매수 거래대금
parts = []
for mkt in ['KOSPI', 'KOSDAQ']:
    for inv in ['외국인', '기관합계']:
        d = stock.get_market_net_purchases_of_equities(DATE, DATE, mkt, inv).reset_index()
        d['시장'] = mkt
        d['투자자'] = inv
        parts.append(d)
pd.concat(parts).to_json(f'{WORK}/krx_netbuy_{DATE}.json', orient='records', force_ascii=False)

# 3) 투자자별 순매수 거래대금 합계 (코스피/코스닥, 개인·외국인·기관) — flow_tbl에 바로 쓰임
flow = {}
for mkt in ['KOSPI', 'KOSDAQ']:
    try:
        d = stock.get_market_trading_value_by_investor(DATE, DATE, mkt)
        flow[mkt] = {
            '개인': round(float(d.loc['개인', '순매수']) / 1e8) if '개인' in d.index else None,
            '외국인': round(float(d.loc['외국인', '순매수']) / 1e8) if '외국인' in d.index else None,
            '기관': round(float(d.loc['기관합계', '순매수']) / 1e8) if '기관합계' in d.index else None,
        }
    except Exception as e:
        flow[mkt] = None
        print(f'{mkt} 수급 조회 실패: {e}')

with open(f'{WORK}/krx_flow_{DATE}.json', 'w', encoding='utf-8') as f:
    json.dump(flow, f, ensure_ascii=False, indent=1)

print('DATE', DATE)
print('flow', flow)
print(f'저장: krx_ohlcv_{DATE}.json, krx_netbuy_{DATE}.json, krx_flow_{DATE}.json')
