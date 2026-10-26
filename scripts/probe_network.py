"""Phase 1 스파이크: GitHub 러너에서 각 출처가 통하는지 확인한다.
값(토큰, 키, 데이터 내용)은 출력하지 않고 HTTP 상태·행 수·성공 여부만 출력한다."""
import json, os, sys, datetime as dt
import requests

def line(name, ok, detail=""):
    print(f"[{'OK' if ok else 'FAIL'}] {name}  {detail}")

# 1) Yahoo Finance
try:
    r = requests.get("https://query1.finance.yahoo.com/v8/finance/chart/%5EGSPC?range=5d&interval=1d",
                     headers={"User-Agent": "Mozilla/5.0"}, timeout=15)
    line("Yahoo Finance (^GSPC)", r.status_code == 200, f"HTTP {r.status_code}")
except Exception as e:
    line("Yahoo Finance", False, type(e).__name__)

# 2) 키움 인증. KIWOOM_PAIRS 에 [[key, secret], ...] JSON 이 있으면 3쌍을 모두 시험하고,
#    없으면 KIWOOM_APP_KEY/SECRET 한 쌍만 시험한다. 쌍 번호와 결과만 출력한다.
def kiwoom_try(idx, k, s):
    try:
        r = requests.post("https://api.kiwoom.com/oauth2/token", timeout=10,
                          json={"grant_type": "client_credentials", "appkey": k, "secretkey": s})
        d = r.json() if r.headers.get("content-type", "").startswith("application/json") else {}
        ok = bool(d.get("token"))
        diag = ""
        if not ok:
            # 값은 출력하지 않고 키움 응답 코드·메시지와 입력 길이(공백 여부 확인용)만 출력한다.
            diag = f"return_code={d.get('return_code')} return_msg={d.get('return_msg')} key_len={len(k)} secret_len={len(s)} key_has_space={' ' in k or k != k.strip()}"
        line(f"키움 쌍 {idx} 토큰 발급", ok, f"HTTP {r.status_code} {diag}")
        if ok:
            h = {"Content-Type": "application/json;charset=UTF-8",
                 "authorization": f"Bearer {d['token']}", "api-id": "ka20006"}
            r2 = requests.post("https://api.kiwoom.com/api/dostk/chart", headers=h, timeout=15,
                               json={"inds_cd": "001", "base_dt": dt.date.today().strftime("%Y%m%d")})
            rows = r2.json().get("inds_dt_pole_qry", []) if r2.status_code == 200 else []
            line(f"키움 쌍 {idx} ka20006 코스피 일봉", len(rows) > 0, f"HTTP {r2.status_code}, 행 {len(rows)}")
        return ok
    except Exception as e:
        line(f"키움 쌍 {idx}", False, type(e).__name__)
        return False

pairs = []
if os.environ.get("KIWOOM_PAIRS"):
    pairs = json.loads(os.environ["KIWOOM_PAIRS"])
elif os.environ.get("KIWOOM_APP_KEY") and os.environ.get("KIWOOM_APP_SECRET"):
    pairs = [[os.environ["KIWOOM_APP_KEY"], os.environ["KIWOOM_APP_SECRET"]]]
if not pairs:
    line("키움", False, "키 미설정")
for i, (k, s) in enumerate(pairs, 1):
    kiwoom_try(i, k, s)

# 3) KRX (pykrx)
try:
    from pykrx import stock
    d = dt.date.today().strftime("%Y%m%d")
    df = stock.get_market_ohlcv_by_ticker(d, market="KOSPI")
    line("KRX pykrx 시세", len(df) > 0, f"행 {len(df)}")
except Exception as e:
    line("KRX pykrx", False, type(e).__name__)

# 3-1) KRX 지수 일봉 (코스피 1001, 코스닥 2001) — 키움 대체 후보
try:
    from pykrx import stock
    end = dt.date.today().strftime("%Y%m%d")
    start = (dt.date.today() - dt.timedelta(days=100)).strftime("%Y%m%d")
    idf = stock.get_index_ohlcv_by_date(start, end, "1001")
    line("KRX pykrx 코스피 지수 일봉", len(idf) > 1, f"행 {len(idf)}, 최근종가 {float(idf['종가'].iloc[-1]) if len(idf) else '-'}")
    idf2 = stock.get_index_ohlcv_by_date(start, end, "2001")
    line("KRX pykrx 코스닥 지수 일봉", len(idf2) > 1, f"행 {len(idf2)}, 최근종가 {float(idf2['종가'].iloc[-1]) if len(idf2) else '-'}")
except Exception as e:
    line("KRX pykrx 지수 일봉", False, type(e).__name__)

# 4) Google Drive (토큰 갱신 + 목록 1건)
try:
    sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
    from upload_pdf import get_service
    svc = get_service()
    svc.files().list(pageSize=1, fields="files(id)").execute()
    line("Google Drive 인증·목록", True)
except Exception as e:
    line("Google Drive", False, type(e).__name__)
