"""국내 지수(코스피·코스닥) 데이터를 키움 REST API(ka20006, 업종일봉조회)로 받아
report_data_{date}.json / charts_{date}.json 안의 코스피·코스닥 항목을 덮어쓴다.
Yahoo Finance(^KS11, ^KQ11) 대신 키움 공식 데이터를 쓰기 위함 (2026-10-25 CEO 지시).
KRX 공식 마감치와 소수점까지 일치하는 것을 확인했다(10/22, 10/23 테스트).

실행 순서: build_report.py를 먼저 돌려 두 JSON을 만든 뒤, 이 스크립트를 실행한다.
사용법: python3 build_kiwoom_domestic.py [기준일YYYYMMDD]  (.env의 KIWOOM_APP_KEY/SECRET 필요)

주의: .env에 KIWOOM_APP_KEY/SECRET이 여러 쌍 들어 있을 수 있다(2026-10-25 기준 3쌍, 그중 1쌍은
깨져 있었음). 이 스크립트는 파일에 나오는 순서대로 각 쌍을 시도해 처음 성공하는 것을 쓴다.
"""
import base64
import io
import json
import os
import sys

import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.patches import Rectangle
import requests
from rsi_signal import simple_rsi, latest as rsi_latest, shade as rsi_shade

import os as _os
plt.rcParams['font.family'] = _os.environ.get('CHART_FONT', 'NanumGothic')
plt.rcParams['axes.unicode_minus'] = False

WORK = os.path.dirname(os.path.abspath(__file__))
DATE = sys.argv[1] if len(sys.argv) > 1 else '20261023'
ENV_PATH = f'{WORK}/../.env'

INDEX_CODE = {'코스피': '001', '코스닥': '101'}


def load_kiwoom_pairs():
    if os.environ.get('KIWOOM_APP_KEY') and os.environ.get('KIWOOM_APP_SECRET'):
        return [(os.environ['KIWOOM_APP_KEY'], os.environ['KIWOOM_APP_SECRET'])]
    pairs = []
    k = s = None
    with open(ENV_PATH, encoding='utf-8') as f:
        for ln in f:
            if ln.startswith('KIWOOM_APP_KEY='):
                k = ln.strip().split('=', 1)[1]
            elif ln.startswith('KIWOOM_APP_SECRET='):
                s = ln.strip().split('=', 1)[1]
                if k:
                    pairs.append((k, s))
                k = None
    return pairs


def get_token():
    for appkey, secretkey in load_kiwoom_pairs():
        r = requests.post('https://api.kiwoom.com/oauth2/token', json={
            'grant_type': 'client_credentials', 'appkey': appkey, 'secretkey': secretkey
        }, timeout=10)
        d = r.json()
        if d.get('token'):
            return d['token']
    raise RuntimeError('KIWOOM_APP_KEY/SECRET 중 인증에 성공한 쌍이 없음. .env 확인 필요.')


def fetch_index_ohlcv(token, inds_cd, base_dt):
    headers = {'Content-Type': 'application/json;charset=UTF-8',
               'authorization': f'Bearer {token}', 'api-id': 'ka20006'}
    r = requests.post('https://api.kiwoom.com/api/dostk/chart', headers=headers,
                       json={'inds_cd': inds_cd, 'base_dt': base_dt}, timeout=15)
    r.raise_for_status()
    rows = r.json().get('inds_dt_pole_qry', [])
    # 최신순으로 오므로 날짜 오름차순으로 뒤집는다 (차트/등락 계산 둘 다 오름차순 전제)
    rows = list(reversed(rows))
    return [{
        'date': row['dt'],
        'open': int(row['open_pric']) / 100,
        'high': int(row['high_pric']) / 100,
        'low': int(row['low_pric']) / 100,
        'close': int(row['cur_prc']) / 100,
    } for row in rows]


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
    ax.set_xlim(-1, len(s))
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
    token = get_token()

    rd_path = f'{WORK}/report_data_{DATE}.json'
    ch_path = f'{WORK}/charts_{DATE}.json'
    RD = json.load(open(rd_path, encoding='utf-8'))
    CH = json.load(open(ch_path, encoding='utf-8'))

    chart_key = {'코스피': 'KS11', '코스닥': 'KQ11'}
    for name, code in INDEX_CODE.items():
        rows = fetch_index_ohlcv(token, code, DATE)
        if len(rows) < 2:
            raise RuntimeError(f'{name} 데이터 부족: {len(rows)}행')
        prev, cur = rows[-2]['close'], rows[-1]['close']
        chg = round(cur - prev, 2)
        pct = round(chg / prev * 100, 2)
        RD['index_rows'][name] = {
            'name': name, 'ticker': f'키움 ka20006 inds_cd={code}',
            'prev': prev, 'close': cur, 'chg': chg, 'pct': pct, 'date': rows[-1]['date'],
        }
        CH[chart_key[name]] = candle(rows, f'{name} 일봉 (최근 60거래일, 키움 ka20006, {DATE[4:6]}/{DATE[6:]} 기준)', chart_key[name])
        RD.setdefault('rsi', {})[chart_key[name]] = rsi_latest(
            [float(r['close']) for r in rows], [f'{r["date"][4:6]}/{r["date"][6:]}' for r in rows])
        print(name, '갱신:', RD['index_rows'][name])

    json.dump(RD, open(rd_path, 'w', encoding='utf-8'), ensure_ascii=False, indent=1, default=str)
    json.dump(CH, open(ch_path, 'w', encoding='utf-8'), ensure_ascii=False)
    print(f'{rd_path}, {ch_path} 의 코스피·코스닥 항목을 키움 데이터로 교체 완료')


if __name__ == '__main__':
    main()
