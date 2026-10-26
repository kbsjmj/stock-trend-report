import json
import sys
import pandas as pd

import os
W = os.path.dirname(os.path.abspath(__file__))

# 작성일 / 기준일(거래일) / 비교용 전일. 새 날짜로 만들 때는 이 세 값만 바꾸면 된다.
# (명령줄 인자로 넘기면 그 값을 쓴다: python3 build_v3_html.py <작성일> <기준일> <전일>)
WRITE_DATE = sys.argv[1] if len(sys.argv) > 1 else '20261024'
DATE = sys.argv[2] if len(sys.argv) > 2 else '20261023'
PREV_DATE = sys.argv[3] if len(sys.argv) > 3 else '20261022'
DATE_SLASH, PREV_SLASH = f'{DATE[4:6]}/{DATE[6:]}', f'{PREV_DATE[4:6]}/{PREV_DATE[6:]}'

RD = json.load(open(f'{W}/report_data_{DATE}.json', encoding='utf-8'))
CH = json.load(open(f'{W}/charts_{DATE}.json', encoding='utf-8'))
IDX, ECO, US = RD['index_rows'], RD['eco_rows'], RD['us_rows']
OUT_HTML = f'{W}/증시추세분석-{WRITE_DATE}-v2.html'

# ---- KRX 공식 수급 (pykrx, 로그인 필요. build_krx.py로 미리 생성). 원 단위 -> 억원 ----
def load_flow(d):
    p = f'{W}/krx_flow_{d}.json'
    if os.path.exists(p):
        return json.load(open(p, encoding='utf-8'))
    return {'KOSPI': None, 'KOSDAQ': None}

FLOW = {DATE_SLASH: load_flow(DATE), PREV_SLASH: load_flow(PREV_DATE)}

oh = pd.read_json(f'{W}/krx_ohlcv_{DATE}.json', dtype={'티커': str})
nb = pd.read_json(f'{W}/krx_netbuy_{DATE}.json', dtype={'티커': str})
oh['티커'] = oh['티커'].str.zfill(6)
nb['티커'] = nb['티커'].str.zfill(6)
piv = nb.pivot_table(index='티커', columns='투자자', values='순매수거래대금', aggfunc='sum')
K = oh.merge(piv, left_on='티커', right_index=True, how='left')
K['외국인'] = K['외국인'] / 1e8
K['기관'] = K['기관합계'] / 1e8
K['거래대금억'] = K['거래대금'] / 1e8
K = K.set_index('티커')

# 국내 관심 종목 (지침 목록, 정정 반영)
KR_THEMES = {
    '반도체': ['삼성전자', 'SK하이닉스', '한미반도체'],
    'MLCC': ['삼성전기', 'LG이노텍', '삼화콘덴서'],
    '2차전지': ['LG에너지솔루션', '삼성SDI', '에코프로'],
    '로봇': ['두산로보틱스', '레인보우로보틱스', '로보티즈'],
    'AI': ['LG전자', '현대오토에버'],
    '원자력': ['두산에너빌리티', '비에이치아이', '우리기술'],
    '태양광': ['OCI홀딩스', '한화솔루션', 'HD현대에너지솔루션'],
    '전력설비': ['HD현대일렉트릭', 'LS ELECTRIC', '산일전기'],
    '전선': ['LS', '가온전선', '대한전선'],
    '스페이스X': ['스피어', '인텔리안테크', '아주IB투자'],
    '방산': ['한화에어로스페이스', 'LIG디펜스앤에어로스페이스', '현대로템'],
    '조선': ['한화오션', 'HD현대중공업', '삼성중공업'],
    '신재생에너지': ['SK이터닉스', 'HD현대에너지솔루션', 'LS머트리얼즈'],
    '광통신': ['대한광통신', '빛샘전자', '우리로'],
    '바이오': ['삼성바이오로직스', '알테오젠', '지투지바이오'],
    '중동재건': ['삼성E&A', '대우건설', '현대건설'],
}
KR_CODE = {'삼성전자': '005930', 'SK하이닉스': '000660', '한미반도체': '042700', '삼성전기': '009150',
           'LG이노텍': '011070', '삼화콘덴서': '001820', 'LG에너지솔루션': '373220', '삼성SDI': '006400',
           '에코프로': '086520', '두산로보틱스': '454910', '레인보우로보틱스': '277810', '로보티즈': '108490',
           'LG전자': '066570', '현대오토에버': '307950', '두산에너빌리티': '034020', '비에이치아이': '083650',
           '우리기술': '032820', 'OCI홀딩스': '010060', '한화솔루션': '009830', 'HD현대에너지솔루션': '322000',
           'HD현대일렉트릭': '267260', 'LS ELECTRIC': '010120', '산일전기': '062040', 'LS': '006260',
           '가온전선': '000500', '대한전선': '001440', '스피어': '347700', '인텔리안테크': '189300',
           '아주IB투자': '027360', '한화에어로스페이스': '012450', 'LIG디펜스앤에어로스페이스': '079550',
           '현대로템': '064350', '한화오션': '042660', 'HD현대중공업': '329180', '삼성중공업': '010140',
           'SK이터닉스': '368770', 'LS머트리얼즈': '417200', '대한광통신': '010170', '빛샘전자': '072950',
           '우리로': '046390', '삼성바이오로직스': '207940', '알테오젠': '196170', '지투지바이오': '456160',
           '삼성E&A': '028050', '대우건설': '047040', '현대건설': '000720'}

# 국내 테마 평균 등락률 (관심 종목 단순 평균)
def kr_row(name):
    code = KR_CODE[name]
    r = K.loc[code]
    return {'name': name, 'code': code, 'close': int(r['종가']), 'pct': float(r['등락률']), 'high': int(r['고가']),
            'open': int(r['시가']), 'low': int(r['저가']), 'turn': float(r['거래대금억']),
            'foreign': r['외국인'], 'inst': r['기관']}

kr_rows = {n: kr_row(n) for n in KR_CODE}
kr_theme_stats = []
for th, names in KR_THEMES.items():
    rows = [kr_rows[n] for n in names]
    kr_theme_stats.append({'theme': th, 'avg': sum(r['pct'] for r in rows) / len(rows),
                           'top': sorted(rows, key=lambda r: r['pct'], reverse=True)[:5]})
kr_theme_stats.sort(key=lambda t: t['avg'], reverse=True)

# 전 종목 상위 (거래대금 10억 이상 조건)
LIQ = K[K['거래대금억'] >= 10]
top_pct = LIQ.sort_values('등락률', ascending=False).head(10)
top_turn = K.sort_values('거래대금억', ascending=False).head(10)


def pct(v):
    c = 'up' if v > 0 else ('down' if v < 0 else '')
    return f'<span class="{c}">{v:+.2f}%</span>'


def n_(v):
    return '-' if pd.isna(v) else f'{v:+,.0f}'


def cls(v):
    return 'up' if v > 0 else ('down' if v < 0 else '')


def us_tr(t, r):
    return (f'<tr><td class="l">{r["name"]} <span class="tk">{t}</span></td><td>{r["close"]:,.2f}</td>'
            f'<td>{pct(r["pct"])}</td><td>{r["high"]:,.2f}</td><td>{r["open"]:,.2f}</td><td>{r["low"]:,.2f}</td>'
            f'<td>{r["turnover_est"] / 1e6:,.0f}</td></tr>')


def kr_tr(r, theme=None, rank=None):
    lead = f'<td>{rank}</td>' if rank is not None else ''
    th = f'<td class="l">{theme}</td>' if theme is not None else ''
    return (f'<tr>{lead}<td class="l">{r["name"]} <span class="tk">{r["code"]}</span></td>{th}'
            f'<td>{r["close"]:,}</td><td>{pct(r["pct"])}</td><td>{r["high"]:,}</td><td>{r["open"]:,}</td>'
            f'<td>{r["low"]:,}</td><td>{r["turn"]:,.0f}</td><td>{n_(r["foreign"])}</td><td>{n_(r["inst"])}</td></tr>')


def kr_top_tr(rank, code, r):
    return (f'<tr><td>{rank}</td><td class="l">{r["종목명"] if "종목명" in r else ""} <span class="tk">{code}</span></td>'
            f'<td>{int(r["종가"]):,}</td><td>{pct(r["등락률"])}</td><td>{int(r["고가"]):,}</td><td>{int(r["시가"]):,}</td>'
            f'<td>{int(r["저가"]):,}</td><td>{r["거래대금억"]:,.0f}</td><td>{n_(r["외국인"])}</td><td>{n_(r["기관"])}</td></tr>')


def name_of(code):
    s = nb[nb['티커'] == code]['종목명']
    return s.iloc[0] if len(s) else code


# ---- 본문 조각 ----
i_sp, i_nq, i_dj, i_sox = IDX['S&P 500'], IDX['나스닥 종합'], IDX['다우존스'], IDX['필라델피아 반도체']
i_ks, i_kq = IDX['코스피'], IDX['코스닥']
e_vix, e_tnx, e_wti, e_krw = ECO['S&P 500 VIX'], ECO['미국 국채 10년물 금리(%)'], ECO['텍사스산 원유(WTI, 선물)'], ECO['원/달러']

eco_tbl = f'''<table>
<thead><tr><th class="l">지표명</th><th>현재가</th><th>등락</th><th>등락률</th></tr></thead>
<tbody>
<tr><td class="l">S&amp;P500 VIX</td><td>{e_vix["close"]:.2f}</td><td class="{cls(e_vix["chg"])}">{e_vix["chg"]:+.2f}</td><td>{pct(e_vix["pct"])}</td></tr>
<tr><td class="l">미국 국채 10년물 이자율</td><td>{e_tnx["close"]:.3f}%</td><td class="{cls(e_tnx["chg"])}">{e_tnx["chg"]:+.3f}%p</td><td>{pct(e_tnx["pct"])}</td></tr>
<tr><td class="l">텍사스 원유 가격 (WTI 선물)</td><td>{e_wti["close"]:.2f}</td><td class="{cls(e_wti["chg"])}">{e_wti["chg"]:+.2f}</td><td>{pct(e_wti["pct"])}</td></tr>
<tr><td class="l">원화환율 (원/달러)</td><td>{e_krw["close"]:,.2f}</td><td class="{cls(e_krw["chg"])}">{e_krw["chg"]:+.2f}</td><td>{pct(e_krw["pct"])}</td></tr>
</tbody></table>'''

us_idx_tbl = f'''<table>
<thead><tr><th class="l">지수</th><th>종가</th><th>등락</th><th>등락률</th></tr></thead>
<tbody>
<tr><td class="l">S&amp;P 500</td><td>{i_sp["close"]:,.2f}</td><td class="{cls(i_sp["chg"])}">{i_sp["chg"]:+,.2f}</td><td>{pct(i_sp["pct"])}</td></tr>
<tr><td class="l">나스닥 종합</td><td>{i_nq["close"]:,.2f}</td><td class="{cls(i_nq["chg"])}">{i_nq["chg"]:+,.2f}</td><td>{pct(i_nq["pct"])}</td></tr>
</tbody></table>
<p class="note">참고: 다우 {i_dj["close"]:,.2f} ({i_dj["pct"]:+.2f}%), 필라델피아 반도체 {i_sox["close"]:,.2f} ({i_sox["pct"]:+.2f}%).</p>'''

kr_idx_tbl = f'''<table>
<thead><tr><th class="l">지수</th><th>종가</th><th>등락</th><th>등락률</th></tr></thead>
<tbody>
<tr><td class="l">코스피</td><td>{i_ks["close"]:,.2f}</td><td class="{cls(i_ks["chg"])}">{i_ks["chg"]:+,.2f}</td><td>{pct(i_ks["pct"])}</td></tr>
<tr><td class="l">코스닥</td><td>{i_kq["close"]:,.2f}</td><td class="{cls(i_kq["chg"])}">{i_kq["chg"]:+,.2f}</td><td>{pct(i_kq["pct"])}</td></tr>
</tbody></table>'''

f23, f22 = FLOW[DATE_SLASH], FLOW[PREV_SLASH]  # 변수명은 유지(과거 호환), 실제로는 DATE/PREV_DATE 값
def flow_row(label, d):
    if not d:
        return f'<tr><td class="l">{label}</td><td colspan="3">확인 불가 (krx_flow 파일 없음. build_krx.py 먼저 실행)</td></tr>'
    return (f'<tr><td class="l">{label}</td>'
            f'<td class="{cls(d["개인"])}">{d["개인"]:+,}</td>'
            f'<td class="{cls(d["외국인"])}">{d["외국인"]:+,}</td>'
            f'<td class="{cls(d["기관"])}">{d["기관"]:+,}</td></tr>')

flow_tbl = f'''<table>
<thead><tr><th class="l">시장 / 날짜</th><th>개인</th><th>외국인</th><th>기관</th></tr></thead>
<tbody>
{flow_row(f"코스피 {DATE_SLASH}", f23.get("KOSPI") if f23 else None)}
{flow_row(f"코스닥 {DATE_SLASH}", f23.get("KOSDAQ") if f23 else None)}
{flow_row(f"코스피 {PREV_SLASH}", f22.get("KOSPI") if f22 else None)}
{flow_row(f"코스닥 {PREV_SLASH}", f22.get("KOSDAQ") if f22 else None)}
<tr><td class="l">선물 (기관·외국인·개인)</td><td colspan="3">확인 불가 (pykrx 1.2.9는 지수 선물 수급을 지원하지 않음)</td></tr>
</tbody></table>'''

# 코스피 10/23 안전 접근(섹션 1 요약 문구용). 수급 파일이 없으면 None.
f23_kospi = (f23 or {}).get('KOSPI') or {'개인': 0, '외국인': 0, '기관': 0}
f23_kosdaq = (f23 or {}).get('KOSDAQ') or {'개인': 0, '외국인': 0, '기관': 0}

# 미국 테마 (수집 데이터 기반)
us_theme_tbl = ''
for i, t in enumerate(RD['theme_stats'][:5], 1):
    mem = ', '.join(f'{m["name"]} {m["pct"]:+.2f}%' for _, m in t['top'][:5])
    us_theme_tbl += f'<tr><td>{i}</td><td class="l">{t["theme"]}</td><td>{pct(t["avg"])}</td><td class="l">{mem}</td></tr>'

us_valid = [(t, r) for t, r in US.items() if r]
us_top_pct = sorted(us_valid, key=lambda x: x[1]['pct'], reverse=True)[:10]
us_top_turn = sorted(us_valid, key=lambda x: x[1]['turnover_est'], reverse=True)[:10]
us_pct_tbl = ''.join(f'<tr><td>{i}</td>' + us_tr(t, r)[4:] for i, (t, r) in enumerate(us_top_pct, 1))
us_turn_tbl = ''.join(f'<tr><td>{i}</td>' + us_tr(t, r)[4:] for i, (t, r) in enumerate(us_top_turn, 1))
us_watch_tbl = ''.join(us_tr(t, r) for t, r in us_valid)

# 국내 테마 표
kr_theme_tbl = ''
for i, t in enumerate(kr_theme_stats[:5], 1):
    mem = ', '.join(f'{m["name"]} {m["pct"]:+.2f}%' for m in t['top'])
    kr_theme_tbl += f'<tr><td>{i}</td><td class="l">{t["theme"]}</td><td>{pct(t["avg"])}</td><td class="l">{mem}</td></tr>'

kr_pct_tbl = ''
for i, (code, r) in enumerate(top_pct.iterrows(), 1):
    kr_pct_tbl += (f'<tr><td>{i}</td><td class="l">{name_of(code)} <span class="tk">{code}</span></td>'
                   f'<td>{int(r["종가"]):,}</td><td>{pct(r["등락률"])}</td><td>{int(r["고가"]):,}</td><td>{int(r["시가"]):,}</td>'
                   f'<td>{int(r["저가"]):,}</td><td>{r["거래대금억"]:,.0f}</td><td>{n_(r["외국인"])}</td><td>{n_(r["기관"])}</td></tr>')
kr_turn_tbl = ''
for i, (code, r) in enumerate(top_turn.iterrows(), 1):
    kr_turn_tbl += (f'<tr><td>{i}</td><td class="l">{name_of(code)} <span class="tk">{code}</span></td>'
                    f'<td>{int(r["종가"]):,}</td><td>{pct(r["등락률"])}</td><td>{int(r["고가"]):,}</td><td>{int(r["시가"]):,}</td>'
                    f'<td>{int(r["저가"]):,}</td><td>{r["거래대금억"]:,.0f}</td><td>{n_(r["외국인"])}</td><td>{n_(r["기관"])}</td></tr>')

kr_watch_tbl = ''
for th, names in KR_THEMES.items():
    for n in names:
        kr_watch_tbl += kr_tr(kr_rows[n], theme=th)

us_tbl_nodata = [t for t, r in US.items() if not r]


def img(k):
    return f'<img alt="{k}" src="data:image/png;base64,{CH[k]}" style="width:100%;height:auto">'

EOF_MARK = '__END__'
