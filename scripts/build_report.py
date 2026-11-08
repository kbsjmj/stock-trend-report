"""증시추세분석 초안 생성: 무료 데이터(Yahoo Finance via yfinance)만 사용.
KRX(pykrx) 수급·전체 순위는 build_krx.py가 담당한다.
사용법: python3 build_report.py [YYYYMMDD]  (기준일, 기본값 20261023)"""
import base64, io, json, sys
import datetime as dt
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.patches import Rectangle
import yfinance as yf
from rsi_signal import simple_rsi, latest as rsi_latest, shade as rsi_shade

import os as _os
plt.rcParams['font.family'] = _os.environ.get('CHART_FONT', 'NanumGothic')
plt.rcParams['axes.unicode_minus'] = False

DATE = sys.argv[1] if len(sys.argv) > 1 else '20261023'
_d = dt.date(int(DATE[:4]), int(DATE[4:6]), int(DATE[6:]))
START = (_d - dt.timedelta(days=200)).isoformat()
END = (_d + dt.timedelta(days=1)).isoformat()  # 종료일은 배타적 상한. DATE를 마지막 거래일로 고정
import os
WORK = os.path.dirname(os.path.abspath(__file__))


def _missing(df, tickers):
    """종가가 비어 있는 종목 목록 (yfinance 'database is locked' 등 일시 실패 감지)."""
    tks = [tickers] if isinstance(tickers, str) else list(tickers)
    bad = []
    for t in tks:
        try:
            if len(df[t]['Close'].dropna()) < 2:
                bad.append(t)
        except Exception:
            bad.append(t)
    return bad


def dl(tickers, start=START, end=END, tries=4):
    """yfinance 다운로드. 일시 실패(캐시 DB 잠금 등)는 간격을 두고 재시도한다."""
    import time
    last_bad = []
    for i in range(tries):
        df = yf.download(tickers, start=start, end=end, progress=False,
                         auto_adjust=False, group_by='ticker')
        last_bad = _missing(df, tickers) if df is not None and len(df) else list(
            [tickers] if isinstance(tickers, str) else tickers)
        if not last_bad:
            return df
        print(f"[dl] 재시도 {i + 1}/{tries}: 종가 없음 {last_bad}", flush=True)
        time.sleep(20 * (i + 1))
    # 끝까지 비어 있는 종목은 경고만 남기고 반환한다. 지수 등 필수 종목은 last2()가 명확한 오류로 막는다.
    print(f"[dl] 경고: 재시도 후에도 종가 없음 {last_bad} (해당 종목은 제외하고 진행)", flush=True)
    return df


def last2(df, t):
    s = df[t]['Close'].dropna()
    if len(s) < 2:
        raise RuntimeError(f"종가 데이터 부족: {t} ({len(s)}건)")
    return s.iloc[-2], s.iloc[-1], s.index[-1].date()


# ---- 1. 지수·경제지표 ----
IDX = {'S&P 500': '^GSPC', '나스닥 종합': '^IXIC', '다우존스': '^DJI', '필라델피아 반도체': '^SOX',
       '코스피': '^KS11', '코스닥': '^KQ11'}
ECO = {'S&P 500 VIX': '^VIX', '미국 국채 10년물 금리(%)': '^TNX', '텍사스산 원유(WTI, 선물)': 'CL=F', '원/달러': 'KRW=X'}
idx_df = dl(list(IDX.values()) + list(ECO.values()))

def row(name, t, df, digits=2):
    prev, cur, d = last2(df, t)
    chg = cur - prev
    pct = chg / prev * 100
    return {'name': name, 'ticker': t, 'prev': round(float(prev), digits), 'close': round(float(cur), digits),
            'chg': round(float(chg), digits), 'pct': round(float(pct), 2), 'date': str(d)}

index_rows = {k: row(k, v, idx_df) for k, v in IDX.items()}
eco_rows = {k: row(k, v, idx_df, 3) for k, v in ECO.items()}

# ---- 2. 캔들차트 (최근 100거래일) ----
def candle(ticker, title, fname):
    full = idx_df[ticker].dropna()
    rsi = simple_rsi([float(c) for c in full['Close']])[-100:]
    s = full.tail(100)
    title = title.replace('10/23', s.index[-1].strftime('%m/%d'))
    fig, ax = plt.subplots(figsize=(9.6, 2.5), dpi=140)
    rsi_shade(ax, rsi)
    for i, (dt, r) in enumerate(s.iterrows()):
        o, h, l, c = r['Open'], r['High'], r['Low'], r['Close']
        col = '#c8372d' if c >= o else '#1f5fd1'
        ax.plot([i, i], [l, h], color=col, lw=0.8)
        ax.add_patch(Rectangle((i - 0.35, min(o, c)), 0.7, max(abs(c - o), 1e-9), color=col))
    last_c, prev_c = float(full['Close'].iloc[-1]), float(full['Close'].iloc[-2])
    box = '#c8372d' if last_c >= prev_c else '#1f5fd1'
    ax.set_xlim(-1, len(s) + 8)
    ax.axhline(last_c, color='#c8372d', ls='--', lw=0.8)
    ax.annotate(f'{last_c:,.2f}', xy=(len(s) - 1, last_c), xytext=(len(s) + 0.5, last_c),
                va='center', fontsize=7, color='white', annotation_clip=False,
                bbox=dict(boxstyle='square,pad=0.25', fc=box, ec='none'))
    ax.set_xticks(range(0, len(s), 10))
    ax.set_xticklabels([d.strftime('%m/%d') for d in s.index[::10]], fontsize=7)
    ax.grid(axis='y', alpha=0.3)
    ax.set_title(title, fontsize=9.5)
    ax.tick_params(axis='y', labelsize=7)
    fig.tight_layout()
    path = f'{WORK}/{fname}.png'
    fig.savefig(path)
    plt.close(fig)
    with open(path, 'rb') as f:
        return base64.b64encode(f.read()).decode()

charts = {
    'SPX': candle('^GSPC', 'S&P 500 일봉 (최근 100거래일, 10/23 기준)', 'chart_spx'),
    'IXIC': candle('^IXIC', '나스닥 종합 일봉 (최근 100거래일, 10/23 기준)', 'chart_ixic'),
    'KS11': candle('^KS11', '코스피 일봉 (최근 100거래일, 10/23 기준)', 'chart_kospi'),
    'KQ11': candle('^KQ11', '코스닥 일봉 (최근 100거래일, 10/23 기준)', 'chart_kosdaq'),
}
rsi_rows = {}
for key, t in (('SPX', '^GSPC'), ('IXIC', '^IXIC')):
    full = idx_df[t].dropna()
    rsi_rows[key] = rsi_latest([float(c) for c in full['Close']], [f'{d.month:02d}/{d.day:02d}' for d in full.index])

# ---- 3. 미국 관심 종목 ----
US_THEMES = {
    'BigTech': ['AAPL', 'NVDA', 'MSFT', 'GOOGL', 'AMZN', 'META', 'TSLA', 'SPCX'],
    '반도체': ['SOXX', 'TSM', 'ASML', 'SNDK', 'AVGO', 'MU'],
    'AI': ['PLTR'],
    '로봇': ['BOTZ', 'ISRG', 'TER', 'AVAV', 'ABRA', 'PATH'],
    '2차전지': ['LIT', 'ALB', 'QS', 'LAC'],
    '우주항공': ['ASTS', 'FLV', 'LUNR', 'RKLB'],
    '원자력': ['URA', 'CEG', 'OKLO', 'SMR'],
    '태양광': ['TAN', 'FSLR', 'NEE', 'ENPH'],
    '양자컴퓨터': ['IBM', 'BAH', 'IONQ', 'RGTI'],
}
US_NAMES = {'AAPL': '애플', 'NVDA': '엔비디아', 'MSFT': '마이크로소프트', 'GOOGL': '알파벳A', 'AMZN': '아마존닷컴',
            'META': '메타', 'TSLA': '테슬라', 'SPCX': '스페이스X(상장 여부 재확인)', 'SOXX': '반도체 ETF(SOXX)',
            'TSM': 'TSMC', 'ASML': 'ASML', 'SNDK': '샌디스크', 'AVGO': '브로드컴', 'MU': '마이크론', 'PLTR': '팔란티어',
            'BOTZ': '로봇·AI ETF(BOTZ)', 'ISRG': '인튜이티브서지컬', 'TER': '테라다인', 'AVAV': '에어로바이런먼트',
            'ABRA': '지브라테크놀로지스', 'PATH': '유아이패스', 'LIT': '리튬 ETF(LIT)', 'ALB': '알버말', 'QS': '퀀텀스케이프',
            'LAC': '리튬아메리카스', 'ASTS': 'AST 스페이스모바일', 'FLV': '파이어플라이 에어로스페이스',
            'LUNR': '인튜이티브머신스', 'RKLB': '로켓랩', 'URA': '원자력 ETF(URA)', 'CEG': '컨스텔레이션 에너지',
            'OKLO': '오클로', 'SMR': '뉴스케일 파워(SMR)', 'TAN': '태양광 ETF(TAN)', 'FSLR': '퍼스트솔라',
            'NEE': '넥스트에라 에너지', 'ENPH': '엔페이즈', 'IBM': 'IBM', 'BAH': '부즈앨런해밀턴', 'IONQ': '아이온큐',
            'RGTI': '리게티컴퓨팅'}
us_all = sorted({t for v in US_THEMES.values() for t in v})
us_df = dl(us_all, start='2026-10-19', end=END)

us_rows = {}
for t in us_all:
    try:
        s = us_df[t].dropna()
        prev, cur = s.iloc[-2], s.iloc[-1]
        r = s.iloc[-1]
        us_rows[t] = {'name': US_NAMES[t], 'close': round(float(cur['Close']), 2),
                      'pct': round(float((cur['Close'] / prev['Close'] - 1) * 100), 2),
                      'high': round(float(r['High']), 2), 'open': round(float(r['Open']), 2),
                      'low': round(float(r['Low']), 2),
                      'turnover_est': float(r['Close'] * r['Volume'])}
    except Exception:
        us_rows[t] = None  # 데이터 없음
missing_us = [t for t, v in us_rows.items() if v is None]

theme_stats = []
for th, ts in US_THEMES.items():
    members = [(t, us_rows[t]) for t in ts if us_rows.get(t)]
    if not members:
        continue
    avg = sum(m['pct'] for _, m in members) / len(members)
    top5 = sorted(members, key=lambda x: x[1]['pct'], reverse=True)[:5]
    theme_stats.append({'theme': th, 'avg': round(avg, 2), 'n': len(members), 'top': top5})
theme_stats.sort(key=lambda x: x['avg'], reverse=True)

# ---- 4. 국내 관심 종목 (Yahoo .KS/.KQ, 수급은 KRX 로그인 필요로 확인 불가) ----
KR_THEMES = {
    '반도체': ['삼성전자', 'SK하이닉스', '한미반도체'], 'MLCC': ['삼성전기', 'LG이노텍', '삼화콘덴서'],
    '2차전지': ['LG에너지솔루션', '삼성SDI', '에코프로'], '로봇': ['두산로보틱스', '레인보우로보틱스', '로보티즈'],
    'AI': ['LG전자', '현대오토에버'], '원자력': ['두산에너빌리티', '비에이치아이', '우리기술'],
    '태양광': ['OCI홀딩스', '한화솔루션', 'HD현대에너지솔루션'], '전력설비': ['HD현대일렉트릭', 'LS ELECTRIC', '산일전기'],
    '전선': ['LS', '가온전선', '대한전선'], '스페이스X': ['인텔리안테크', '아주IB투자'],
    '방산': ['한화에어로스페이스', 'LIG디펜스앤에어로스페이스', '현대로템'], '조선': ['한화오션', 'HD현대중공업', '삼성중공업'],
    '신재생에너지': ['SK이터닉스', 'HD현대에너지솔루션'], '광통신': ['대한광통신', '우리로'],
    '바이오': ['삼성바이오로직스', '알테오젠'], '중동재건': ['삼성E&A', '대우건설', '현대건설'],
}
KR_CODE = {'삼성전자': '005930', 'SK하이닉스': '000660', '한미반도체': '042700', '삼성전기': '009150', 'LG이노텍': '011070',
           '삼화콘덴서': '001820', 'LG에너지솔루션': '373220', ' 삼성SDI': '006400', '에코프로': '086520',
           '두산로보틱스': '454910', '레인보우로보틱스': '277810', '로보티즈': '108490', 'LG전자': '066570',
           '현대오토에버': '307950', '두산에너빌리티': '034020', '비에이치아이': '083650', '우리기술': '032820',
           'OCI홀딩스': '010060', '한화솔루션': '009830', 'HD현대에너지솔루션': '322000', 'HD현대일렉트릭': '267260',
           'LS ELECTRIC': '010120', '산일전기': '062040', 'LS': '006260', '가온전선': '000500', '대한전선': '001440',
           '인텔리안테크': '189300', '아주IB투자': '027360', '한화에어로스페이스': '012450',
           'LIG디펜스앤에어로스페이스': '079550', '현대로템': '064350', '한화오션': '042660', 'HD현대중공업': '329180',
           '삼성중공업': '010140', 'SK이터닉스': '368770', '대한광통신': '010170', '우리로': '046390',
           '삼성바이오로직스': '207940', '알테오젠': '196170', '삼성E&A': '028050', '대우건설': '047040', '현대건설': '000720'}
KQ_ONLY = {'에코프로', '비에이치아이', '우리기술', '대한광통신', '우리로', '알테오젠', '레인보우로보틱스', '로보티즈', '두산로보틱스'}
kr_df = dl([c + '.KS' for c in KR_CODE.values()] + [c + '.KQ' for c in KR_CODE.values()], start='2026-10-19', end=END)

kr_rows = {}
for name, code in KR_CODE.items():
    key = name.strip()
    for suffix in ('.KQ', '.KS') if key in KQ_ONLY else ('.KS', '.KQ'):
        try:
            s = kr_df[code + suffix].dropna()
            if len(s) < 2:
                continue
            prev, cur = s.iloc[-2], s.iloc[-1]
            kr_rows[key] = {'code': code + suffix, 'close': round(float(cur['Close'])), 'pct': round(float((cur['Close'] / prev['Close'] - 1) * 100), 2),
                            'high': round(float(cur['High'])), 'open': round(float(cur['Open'])), 'low': round(float(cur['Low'])),
                            'turnover_est': float(cur['Close'] * cur['Volume'])}
            break
        except Exception:
            continue
    else:
        kr_rows[key] = None
missing_kr = [k for k, v in kr_rows.items() if v is None]

out = {'index_rows': index_rows, 'eco_rows': eco_rows, 'charts': list(charts.keys()),
       'us_rows': us_rows, 'missing_us': missing_us, 'theme_stats': theme_stats,
       'kr_rows': kr_rows, 'missing_kr': missing_kr, 'kr_themes': KR_THEMES, 'rsi': rsi_rows}
with open(f'{WORK}/report_data_{DATE}.json', 'w', encoding='utf-8') as f:
    json.dump(out, f, ensure_ascii=False, indent=1, default=str)
with open(f'{WORK}/charts_{DATE}.json', 'w', encoding='utf-8') as f:
    json.dump(charts, f)
print(json.dumps({'index': index_rows, 'eco': eco_rows, 'missing_us': missing_us, 'missing_kr': missing_kr}, ensure_ascii=False, indent=1, default=str))
print('THEMES', [(t['theme'], t['avg']) for t in theme_stats])
