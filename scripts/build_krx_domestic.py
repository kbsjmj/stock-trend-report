"""국내 지수(코스피·코스닥) 일봉을 pykrx(KRX 공식 데이터)로 받아
report_data_{date}.json / charts_{date}.json 안의 코스피·코스닥 항목을 채운다.

build_kiwoom_domestic.py를 대체한다. 키움 REST API는 호출하는 쪽의 IP를 사전 등록해야
인증되는데, GitHub Actions 호스팅 러너는 매 실행마다 IP가 달라져(Azure IP 풀, 수백~수천개)
고정 IP 등록 방식과 구조적으로 맞지 않는다(2026-10-27 확인). pykrx가 KRX 공식 데이터를
직접 제공하고 키움과 소수점까지 일치함을 확인했으므로(코스피 5469.47, 코스닥 727.21,
2026-10-26 기준 — 로컬 키움 결과와 동일) 이쪽으로 전환한다. IP 등록이 필요 없다.

실행 순서: build_report.py를 먼저 돌려 두 JSON을 만든 뒤, 이 스크립트를 실행한다.
사용법: python3 build_krx_domestic.py [기준일YYYYMMDD]
"""
import base64
import io
import json
import os
import sys
import datetime as dt

import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.patches import Rectangle
from pykrx import stock
from rsi_signal import simple_rsi, latest as rsi_latest, shade as rsi_shade

plt.rcParams['font.family'] = os.environ.get('CHART_FONT', 'NanumGothic')
plt.rcParams['axes.unicode_minus'] = False

WORK = os.path.dirname(os.path.abspath(__file__))
DATE = sys.argv[1] if len(sys.argv) > 1 else '20261023'

# pykrx 지수 티커: 코스피 1001, 코스닥 2001
INDEX_CODE = {'코스피': '1001', '코스닥': '2001'}


def fetch_index_ohlcv(ticker, base_dt):
    end = dt.datetime.strptime(base_dt, '%Y%m%d').date()
    start = (end - dt.timedelta(days=120)).strftime('%Y%m%d')  # 60거래일 확보용 여유
    df = stock.get_index_ohlcv_by_date(start, base_dt, ticker)
    rows = []
    for idx, row in df.iterrows():
        rows.append({
            'date': idx.strftime('%Y%m%d'),
            'open': float(row['시가']),
            'high': float(row['고가']),
            'low': float(row['저가']),
            'close': float(row['종가']),
        })
    return rows


def candle(rows, title, fname):
    rsi = simple_rsi([float(r['close']) for r in rows])[-60:]
    s = rows[-60:]
    fig, ax = plt.subplots(figsize=(7.4, 2.5), dpi=140)
    rsi_shade(ax, rsi)
    for i, r in enumerate(s):
        o, h, l, c = r['open'], r['high'], r['low'], r['close']
        col = '#c8372d' if c >= o else '#1f5fd1'
        ax.plot([i, i], [l, h], color=col, lw=0.8)
        ax.add_patch(Rectangle((i - 0.35, min(o, c)), 0.7, max(abs(c - o), 1e-9), color=col))
    last_c, prev_c = float(rows[-1]['close']), float(rows[-2]['close'])
    box = '#c8372d' if last_c >= prev_c else '#1f5fd1'
    ax.set_xlim(-1, len(s) + 8)
    ax.axhline(last_c, color='#c8372d', ls='--', lw=0.8)
    ax.annotate(f'{last_c:,.2f}', xy=(len(s) - 1, last_c), xytext=(len(s) + 0.5, last_c),
                va='center', fontsize=7, color='white', annotation_clip=False,
                bbox=dict(boxstyle='square,pad=0.25', fc=box, ec='none'))
    ax.set_xticks(range(0, len(s), 10))
    ax.set_xticklabels([f'{d["date"][4:6]}/{d["date"][6:]}' for d in s[::10]], fontsize=7)
    ax.grid(axis='y', alpha=0.3)
    ax.set_title(title, fontsize=9.5)
    ax.tick_params(axis='y', labelsize=7)
    fig.tight_layout()
    buf = io.BytesIO()
    fig.savefig(buf, format='png')
    plt.close(fig)
    return base64.b64encode(buf.getvalue()).decode()


def main():
    rd_path = f'{WORK}/report_data_{DATE}.json'
    ch_path = f'{WORK}/charts_{DATE}.json'
    RD = json.load(open(rd_path, encoding='utf-8'))
    CH = json.load(open(ch_path, encoding='utf-8'))

    chart_key = {'코스피': 'KS11', '코스닥': 'KQ11'}
    for name, code in INDEX_CODE.items():
        rows = fetch_index_ohlcv(code, DATE)
        if len(rows) < 2:
            raise RuntimeError(f'{name} 데이터 부족: {len(rows)}행')
        prev, cur = rows[-2]['close'], rows[-1]['close']
        chg = round(cur - prev, 2)
        pct = round(chg / prev * 100, 2)
        RD['index_rows'][name] = {
            'name': name, 'ticker': f'pykrx 지수 {code}',
            'prev': prev, 'close': cur, 'chg': chg, 'pct': pct, 'date': rows[-1]['date'],
        }
        CH[chart_key[name]] = candle(rows, f'{name} 일봉 (최근 60거래일, KRX, {DATE[4:6]}/{DATE[6:]} 기준)', chart_key[name])
        RD.setdefault('rsi', {})[chart_key[name]] = rsi_latest(
            [float(r['close']) for r in rows], [f'{r["date"][4:6]}/{r["date"][6:]}' for r in rows])
        print(name, '갱신:', RD['index_rows'][name])

    json.dump(RD, open(rd_path, 'w', encoding='utf-8'), ensure_ascii=False, indent=1, default=str)
    json.dump(CH, open(ch_path, 'w', encoding='utf-8'), ensure_ascii=False)
    print(f'{rd_path}, {ch_path} 의 코스피·코스닥 항목을 KRX(pykrx) 데이터로 교체 완료')


if __name__ == '__main__':
    main()
