"""전 종목 10/26(기준일) 시세 + 종목별 외국인·기관·개인 순매수를 pykrx로 받아 JSON으로 저장.
6-4 국내 주요 관심 종목 표를 채우기 위한 일회성 조회. 사용법: python3 fetch_kr_watch.py YYYYMMDD
전일 종가는 직전 거래일(기준일 이전 영업일)의 종가로 계산한다.
"""
import json
import os
import sys

import pandas as pd
from pykrx import stock

WORK = os.path.dirname(os.path.abspath(__file__))
DATE = sys.argv[1]
PREV = sys.argv[2]  # 직전 거래일 (예: 20261026 기준이면 20261023)

rows = {}
for mkt in ['KOSPI', 'KOSDAQ']:
    df = stock.get_market_ohlcv_by_ticker(DATE, market=mkt)
    prev_df = stock.get_market_ohlcv_by_ticker(PREV, market=mkt)
    for code, r in df.iterrows():
        prev_close = float(prev_df.loc[code, '종가']) if code in prev_df.index else None
        rows[code] = {
            'market': mkt, 'close': float(r['종가']), 'pct': float(r['등락률']),
            'open': float(r['시가']), 'high': float(r['고가']), 'low': float(r['저가']),
            'turn_won': float(r['거래대금']), 'prev_close': prev_close,
        }

# 종목명
for mkt in ['KOSPI', 'KOSDAQ']:
    for code in stock.get_market_ticker_list(DATE, market=mkt):
        rows.setdefault(code, {})['name'] = stock.get_market_ticker_name(code)

# 종목별 외국인·기관·개인 순매수 거래대금 (원)
for mkt in ['KOSPI', 'KOSDAQ']:
    for inv_key, inv in [('foreign_won', '외국인'), ('inst_won', '기관합계'), ('retail_won', '개인')]:
        d = stock.get_market_net_purchases_of_equities(DATE, DATE, mkt, inv).reset_index()
        for _, r in d.iterrows():
            code = str(r['티커']).zfill(6)
            if code in rows:
                rows[code][inv_key] = float(r['순매수거래대금'])

# 검증: 전일 종가로 계산한 등락률이 pykrx 등락률과 맞는지
mismatch = 0
for code, r in rows.items():
    if r.get('prev_close'):
        calc = (r['close'] / r['prev_close'] - 1) * 100
        if abs(calc - r['pct']) > 0.02:
            mismatch += 1
print(f'종목 수: {len(rows)}, 등락률 불일치(>0.02%p): {mismatch}')

out_path = f'{WORK}/kr_watch_{DATE}.json'
with open(out_path, 'w', encoding='utf-8') as f:
    json.dump(rows, f, ensure_ascii=False, indent=0)
print('저장:', out_path)
