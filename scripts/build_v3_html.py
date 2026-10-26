import os
_HERE = os.path.dirname(os.path.abspath(__file__))
exec(open(os.path.join(_HERE, 'build_v3.py'), encoding='utf-8').read())

CSS = '''
@page { size: A4; margin: 14mm 12mm; }
body { font-family: "Apple SD Gothic Neo","Noto Sans KR",sans-serif; color:#18202c; font-size:10pt; line-height:1.55; margin:0; }
h1 { font-size:17pt; margin:0 0 4px; }
h2 { font-size:12pt; color:#17375c; margin:16px 0 6px; border-bottom:1px solid #dde2ea; padding-bottom:3px; page-break-after:avoid; break-after:avoid; }
h2 .secnum { font-size:17pt; font-weight:bold; }
h3 { font-size:10.5pt; color:#17375c; margin:12px 0 4px; page-break-after:avoid; break-after:avoid; }
.meta { color:#5d6878; font-size:9pt; margin-bottom:8px; }
.draft { background:#fff4dc; color:#7a5200; border:1px solid #dde2ea; padding:7px 10px; font-size:9pt; margin:8px 0; }
table { border-collapse:collapse; width:100%; margin:4px 0 6px; font-size:8.5pt; }
thead { display:table-header-group; }
tr { page-break-inside:avoid; break-inside:avoid; }
th, td { border-bottom:1px solid #dde2ea; padding:4px 5px; text-align:right; vertical-align:top; }
th { color:#5d6878; font-weight:normal; }
td.l, th.l { text-align:left; }
.tk { color:#5d6878; font-size:7.5pt; }
.up { color:#c8372d; } .down { color:#1f5fd1; }
.note { color:#5d6878; font-size:8.5pt; margin:2px 0 6px; }
ul { margin:3px 0; padding-left:1.2em; } li { margin-bottom:2px; }
.src li { font-size:8.5pt; word-break:break-all; }
.chart { margin:4px 0; page-break-inside:avoid; break-inside:avoid; }
.chart img { max-height:6.2cm; width:100%; object-fit:contain; }
.keep { page-break-inside:avoid; break-inside:avoid; }
.disc { color:#5d6878; font-size:8.5pt; border-top:1px solid #dde2ea; padding-top:6px; margin-top:14px; }
'''


def tbl(header_html, rows_html):
    return f'<table><thead><tr>{header_html}</tr></thead><tbody>{rows_html}</tbody></table>'


import json as _json, html as _html
def _fmt_md(d): return f'{d[4:6]}/{d[6:]}'
_NARR_PATH = os.path.join(_HERE, '..', 'narrative', f'{DATE}.json')
if not os.path.exists(_NARR_PATH):
    raise SystemExit(f'narrative 없음: {_NARR_PATH} -- 1절 원인 문구를 먼저 작성해야 발행한다')
_N = _json.load(open(_NARR_PATH, encoding='utf-8'))
def _ul(items):
    return '<ul>' + ''.join(f'<li>{_html.escape(x)}</li>' for x in items) + '</ul>'
US_HTML = _ul([f'[미국 데이터 시점] 미국 {_fmt_md(DATE)} 정규장은 한국 시간 {_fmt_md(WRITE_DATE)} 새벽에 마감합니다. 이 보고서의 미국 지수 값은 {_fmt_md(DATE)} 종가 기준입니다.'] + _N['us'])
KR_HTML = _ul(_N['kr'])

BODY = f'''
<h1>증시추세분석 ({WRITE_DATE})</h1>
<p class="meta">작성 {WRITE_DATE[4:6]}/{WRITE_DATE[6:]} · 기준: 미국 {DATE_SLASH} 정규장 마감 · 한국 {DATE_SLASH} 마감</p>
<div class="keep">
<h2><span class="secnum">&nbsp;1&nbsp;</span>. 증시 추세 요약</h2>
<h3>1-1. 미국 증시 추세 요약</h3>
{US_HTML}
<h3>1-2. 국내 증시 추세 요약</h3>
{KR_HTML}
<h2><span class="secnum">&nbsp;2&nbsp;</span>. 주요 경제 지표</h2>
{eco_tbl}
<p class="note">WTI는 현물이 아닌 선물 가격입니다. 국채 10년물은 금리(%) 값 그대로이며, 등락은 %p입니다.</p>
</div>

<div style="page-break-before:always; break-before:page;">
<h2><span class="secnum">&nbsp;3&nbsp;</span>. 미국 지수 추세</h2>
<p class="note">지수 값은 현물 종가입니다. 지수 선물 시세는 이번 실행에서 조회하지 못했습니다.</p>
<h3>3-1. 미국 업종 지수</h3>
{us_idx_tbl}
</div>
<div>
<h3>3-2. 미국 업종 차트 (일봉, 최근 60거래일)</h3>
<h3>3-2-1. S&amp;P 500</h3>
<div class="chart">{img("SPX")}</div>
<h3>3-2-2. 나스닥 종합</h3>
<div class="chart">{img("IXIC")}</div>
<p class="note">차트는 Yahoo Finance 일봉으로 직접 그렸습니다. 영웅문 0633 차트(#지도+S&amp;P 500(일), #지도+나스닥 100(일))는 맥에서 조회할 수 없어 사용하지 않았습니다.</p>
</div>

<div style="page-break-before:always; break-before:page;">
<h2><span class="secnum">&nbsp;4&nbsp;</span>. 국내 지수 추세</h2>
<p class="note">지수 값은 현물 종가입니다. 지수 선물 시세는 pykrx가 지원하지 않아 확인 불가입니다.</p>
<h3>4-1. 국내 업종 지수</h3>
{kr_idx_tbl}
<h3>4-2. 국내 증시 수급 (순매수 거래대금, 억원, KRX 공식)</h3>
{flow_tbl}
<p class="note">10/22 기사 값(코스피 개인 +3,802·외국인 +614·기관 -4,621)은 KRX 값과 달라 채택하지 않았습니다.</p>
<h3>4-3. 국내 지수 차트 (일봉, 최근 60거래일)</h3>
<h3>4-3-1. 코스피</h3>
<div class="chart">{img("KS11")}</div>
<h3>4-3-2. 코스닥</h3>
<div class="chart">{img("KQ11")}</div>
</div>

<div class="keep">
<h2><span class="secnum">&nbsp;5&nbsp;</span>. 미국 주요 관심 종목</h2>
<h3>5-1. 미국 상승률 상위 테마 (5개, 관련 종목 5개)</h3>
<p class="note">테마 평균 등락률은 테마에 속한 관심 종목의 단순 평균입니다.</p>
{tbl('<th>순위</th><th class="l">테마</th><th>평균 등락률</th><th class="l">관련 종목 (상위 5)</th>', us_theme_tbl)}
<h3>5-2. 미국 상승률 상위 종목 (관심 종목 내 상위 10)</h3>
<p class="note">전체 시장 순위는 무료 자료로 받을 수 없어 관심 종목 안에서 계산했습니다.</p>
{tbl('<th>순위</th><th class="l">종목명</th><th>현재가</th><th>등락률</th><th>고가</th><th>시가</th><th>저가</th><th>추정 거래대금(백만$)</th>', us_pct_tbl)}
<h3>5-3. 미국 거래대금 상위 종목 (관심 종목 내 상위 10)</h3>
<p class="note">거래대금은 종가×거래량으로 계산한 추정치입니다.</p>
{tbl('<th>순위</th><th class="l">종목명</th><th>현재가</th><th>등락률</th><th>고가</th><th>시가</th><th>저가</th><th>추정 거래대금(백만$)</th>', us_turn_tbl)}
</div>
<h3>5-4. 미국 주요 관심 종목</h3>
{tbl('<th class="l">종목명</th><th>현재가</th><th>등락률</th><th>고가</th><th>시가</th><th>저가</th><th>추정 거래대금(백만$)</th>', us_watch_tbl)}
<p class="note">정정: SK하이닉스(ADM)는 미국 상장 종목이 아니므로 국내 목록(6-4)에 넣었습니다. SNR(뉴스케일)은 티커가 SMR이어서 SMR로 표기했습니다. ABRA(지브라테크놀로지스)는 데이터가 없어 제외했습니다. SPCX(스페이스X)는 데이터가 조회되지만 상장 여부를 한 번 더 확인해야 합니다. TSMC는 티커 TSM으로 표기했습니다.</p>

<div class="keep">
<h2><span class="secnum">&nbsp;6&nbsp;</span>. 국내 주요 관심 종목</h2>
<h3>6-1. 국내 상승률 상위 테마 (5개, 관련 종목 5개)</h3>
<p class="note">테마 평균 등락률은 테마에 속한 관심 종목의 단순 평균입니다.</p>
{tbl('<th>순위</th><th class="l">테마</th><th>평균 등락률</th><th class="l">관련 종목 (상위 5)</th>', kr_theme_tbl)}
<h3>6-2. 국내 상승률 상위 종목 (전 종목, 거래대금 10억원 이상)</h3>
<p class="note">거래대금이 너무 작은 종목의 급등을 빼기 위해 10억원 이상 조건을 두었습니다. 외국인·기관 순매수는 투자자별 순매수 거래대금(억원)입니다.</p>
{tbl('<th>순위</th><th class="l">종목명</th><th>현재가</th><th>등락률</th><th>고가</th><th>시가</th><th>저가</th><th>거래대금(억)</th><th>외국인 순매수(억)</th><th>기관 순매수(억)</th>', kr_pct_tbl)}
<h3>6-3. 국내 거래대금 상위 종목 (전 종목)</h3>
{tbl('<th>순위</th><th class="l">종목명</th><th>현재가</th><th>등락률</th><th>고가</th><th>시가</th><th>저가</th><th>거래대금(억)</th><th>외국인 순매수(억)</th><th>기관 순매수(억)</th>', kr_turn_tbl)}
</div>
<h3>6-4. 국내 주요 관심 종목</h3>
{tbl('<th class="l">종목명</th><th class="l">테마</th><th>현재가</th><th>등락률</th><th>고가</th><th>시가</th><th>저가</th><th>거래대금(억)</th><th>외국인 순매수(억)</th><th>기관 순매수(억)</th>', kr_watch_tbl)}
<p class="note">정정: "레이보우로보틱스"는 "레인보우로보틱스", "알테오진"은 "알테오젠", "지투바이오"는 KRX 등록명 "지투지바이오"(456160)로 표기했습니다. 스피어(347700)는 코스닥 등록명 그대로입니다.</p>

<div class="keep">
<h2><span class="secnum">&nbsp;7&nbsp;</span>. 보고서 작성 출처</h2>
<ul class="src">
<li>한국거래소 정보데이터시스템 (지수, 투자자별 수급, 전 종목 시세, 순매수, 관심 종목): <a href="http://data.krx.co.kr">data.krx.co.kr</a>, 조회 도구 pykrx 1.2.9</li>
<li>Yahoo Finance (미국 지수, 경제지표, 미국 관심 종목, 차트): <a href="https://finance.yahoo.com">finance.yahoo.com</a></li>
<li>키움증권 REST API (국내 지수 코스피·코스닥 시세·차트, ka20006): KRX 공식 마감치와 일치 확인</li>
<li>기사 교차 확인: 10/22 마감 지수와 수급은 이전 보고서 출처(서울신문, 포인트데일리, 뉴스핌, 머니투데이, 이투데이, 한국일보) 대조. 10/23 원인은 미국 쪽 데일리안·공감신문·미디어파인·스페셜경제·스페셜타임스·탑스타뉴스(다우 1.23%↓, 미·이란 긴장·유가 급등 7개 매체 일치, 후티·사우디 언급 매체는 없어 정정), 국내 쪽 서울신문·국제뉴스·뉴스핌·전자신문(코스피 0.30%↑ 5550.30, SK하이닉스 +4.42%·솔리다임 IPO 검토 중단 공시) 교차 확인.</li>
<li>선물 시세·수급: 미확인 (pykrx 미지원)</li>
</ul>
<p class="note">국내 수급·상위 종목·관심 종목은 KRX 정보데이터시스템(pykrx) 공식 자료입니다. 미국 지수·경제지표·관심 종목은 Yahoo Finance 한 곳 값입니다. {DATE_SLASH} 원인은 위처럼 매체 3곳 이상 교차 확인해 반영했습니다(1절 원인 문구는 매번 직접 확인·작성 필요 — 자동 생성 아님). WTI·원/달러는 24시간 거래되는 상품이라 조회 시점에 따라 같은 날짜라도 종가가 조금씩 달라질 수 있습니다.</p>
</div>

<p class="disc">본 보고서는 공개 정보를 요약한 것이며 투자 권유가 아닙니다. 투자 판단과 책임은 본인에게 있습니다.</p>
'''

HTML = f'''<!doctype html>
<html lang="ko"><head><meta charset="utf-8"><title>증시추세분석 ({WRITE_DATE})</title>
<style>{CSS}</style></head><body>{BODY}</body></html>'''

open(OUT_HTML, 'w', encoding='utf-8').write(HTML)
print('written', OUT_HTML, len(HTML))
print('theme us:', [(t['theme'], round(t['avg'], 2)) for t in RD['theme_stats']][:3])
print('theme kr:', [(t['theme'], round(t['avg'], 2)) for t in kr_theme_stats][:5])
print('missing KR codes:', [n for n in KR_CODE if n not in K.index.map(lambda c: KR_CODE.get(n)).tolist()][:3])
