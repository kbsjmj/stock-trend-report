"""국내 종목 행(report_data의 kr_rows)을 KRX(pykrx) 값으로 바로잡는다.

배경(2026-11-10 확인): build_report.py는 국내 종목 가격을 yfinance에서 받는다.
기준일의 국내 종목 봉이 Yahoo에 없으면 마지막 거래일(예: 11/06) 값이 기준일 값으로 들어간다.
그 결과 등락률·종가가 전일과 같아졌다. 지수(코스피·코스닥)와 수급은 pykrx라 영향이 없다.

이 스크립트는 build_krx.py가 만든 krx_ohlcv_{DATE}.json과 krx_ohlcv_{PREV}.json으로
kr_rows의 종가·고가·시가·저가·등락률·거래대금을 KRX 값으로 덮어쓴다.
KRX 기준일 값이 전일과 전 종목 동일하면 날짜 오류로 보고 실패한다.

사용법: python3 patch_kr_rows.py YYYYMMDD PREV_YYYYMMDD
"""
import json
import os
import sys

WORK = os.path.dirname(os.path.abspath(__file__))
DATE, PREV = sys.argv[1], sys.argv[2]


def load_krx(d):
    rows = json.load(open(f'{WORK}/krx_ohlcv_{d}.json', encoding='utf-8'))
    out = {}
    for r in rows:
        out[str(r['티커']).zfill(6)] = r
    return out


cur = load_krx(DATE)
prev = load_krx(PREV)

same = sum(1 for k in cur if k in prev and cur[k]['종가'] == prev[k]['종가'])
if cur and same == len(cur):
    sys.exit(f'KRX {DATE} 종가가 {PREV}와 전 종목 동일하다 -> 날짜 오류로 중단')

rd_path = f'{WORK}/report_data_{DATE}.json'
rd = json.load(open(rd_path, encoding='utf-8'))

changed = []
missing = []
for name, row in rd['kr_rows'].items():
    if not row:
        continue
    code = row['code'][:6]
    c = cur.get(code)
    if c is None:
        missing.append(name)
        continue
    old_close = row.get('close')
    row.update({
        'close': int(c['종가']),
        'high': int(c['고가']),
        'open': int(c['시가']),
        'low': int(c['저가']),
        'pct': round(float(c['등락률']), 2),
        'turnover_est': float(c['거래대금']),
    })
    changed.append((name, old_close, row['close'], row['pct']))

with open(rd_path, 'w', encoding='utf-8') as f:
    json.dump(rd, f, ensure_ascii=False)

print(f'국내 종목 KRX 보정: {len(changed)}건 갱신, KRX에 없음 {len(missing)}건 {missing}')
for name, old, new, pct in changed[:6]:
    print(f'  {name}: 종가 {old} -> {new}, 등락률 {pct:+.2f}%')
