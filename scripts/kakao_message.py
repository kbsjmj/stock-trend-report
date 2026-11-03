"""카카오톡 보고서 알림 문구를 만들고, 전송 기록을 남긴다.

- 전송 자체는 Claude가 PlayMCP KakaotalkChat-MemoChat으로 한다(이 스크립트는 보내지 않는다).
- 매 전송마다 새 파일을 만든다: state/kakao/{WRITE}_{UTC시각}.json. 기존 기록은 덮어쓰지 않는다.

사용법:
  # 문구 만들기 (자동 모드면 같은 작성일 기록이 있으면 건너뛴다)
  python3 kakao_message.py text --key KEY --write WRITE --mode auto|command
  # 전송 성공 후 기록 남기기
  python3 kakao_message.py record --key KEY --write WRITE --version N --link URL

출력(text): JSON 한 줄 {"send": true|false, "reason": "...", "message": "...", "length": N}
 - mode auto: state/kakao/{WRITE}.json 또는 {WRITE}_*.json이 있으면 send=false.
 - mode command: 항상 send=true (보고서 작성 명령).
 - 발행 기록이 없으면 문구는 "발행 기록 없음, 확인 필요"로 바뀐다.
"""
import argparse
import datetime as dt
import glob
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
KAKAO_DIR = ROOT / "state" / "kakao"
PUB_DIR = ROOT / "state" / "published"
DATA_DIR = ROOT / "data"


def mmdd(ymd: str) -> str:
    return f"{ymd[4:6]}/{ymd[6:8]}"


def latest_published(key: str):
    best = None
    for p in PUB_DIR.glob(f"{key}_v*.json"):
        rec = json.loads(p.read_text(encoding="utf-8"))
        if best is None or rec["version"] > best["version"]:
            best = rec
    return best


def index_value(key: str, name: str):
    p = DATA_DIR / f"report_data_{key}.json"
    if not p.exists():
        return None
    return json.loads(p.read_text(encoding="utf-8")).get("index_rows", {}).get(name)


def signed(pct: float) -> str:
    return f"{pct:+.2f}%"


def build_text(key: str, write: str, rec: dict) -> str:
    dt_key = key.split("-w")[0]  # 월요일 키 {DATE}-w{WRITE}면 기준일만 쓴다
    link = rec["webViewLink"].replace("?usp=drivesdk", "")
    parts = []
    for label, name in [("미국 다우", "다우존스"), ("S&P", "S&P 500"),
                        ("나스닥", "나스닥 종합"), ("반도체", "필라델피아 반도체")]:
        v = index_value(dt_key, name)
        parts.append(f"{label} {signed(v['pct'])}" if v else f"{label} 집계 없음")
    us = " ".join(parts)
    kr = []
    for label, name in [("코스피", "코스피"), ("코스닥", "코스닥")]:
        v = index_value(dt_key, name)
        kr.append(f"{label} {v['close']:,.0f} {signed(v['pct'])}" if v else f"{label} 집계 없음")
    head = f"[증시추세분석(클라우드) 작성 {mmdd(write)}·기준 {mmdd(dt_key)}]"
    return f"{head} {us} / {' '.join(kr)} {link}"


def cmd_text(a) -> int:
    write = a.write
    if a.mode == "auto":
        if (KAKAO_DIR / f"{write}.json").exists() or glob.glob(str(KAKAO_DIR / f"{write}_*.json")):
            print(json.dumps({"send": False, "reason": "같은 작성일 전송 기록 있음(자동 모드)"}, ensure_ascii=False))
            return 0
    rec = latest_published(a.key)
    if rec is None:
        head = f"[증시추세분석(클라우드) 작성 {mmdd(write)}·기준 {mmdd(a.key.split('-w')[0])}]"
        msg = f"{head} 발행 기록 없음, 확인 필요"
    else:
        msg = build_text(a.key, write, rec)
    out = {"send": True, "reason": a.mode, "message": msg, "length": len(msg),
           "version": rec["version"] if rec else None}
    if len(msg) > 200:
        out["warning"] = "200자 초과: 지수 항목을 줄여야 한다"
    print(json.dumps(out, ensure_ascii=False))
    return 0


def cmd_record(a) -> int:
    KAKAO_DIR.mkdir(parents=True, exist_ok=True)
    ts = dt.datetime.now(dt.timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    path = KAKAO_DIR / f"{a.write}_{ts}.json"
    rec = {"write": a.write, "key": a.key, "version": a.version, "webViewLink": a.link,
           "sent_at_utc": ts}
    path.write_text(json.dumps(rec, ensure_ascii=False, indent=1), encoding="utf-8")
    print(path)
    return 0


def main() -> int:
    ap = argparse.ArgumentParser()
    sub = ap.add_subparsers(dest="cmd", required=True)
    t = sub.add_parser("text")
    t.add_argument("--key", required=True)
    t.add_argument("--write", required=True)
    t.add_argument("--mode", choices=["auto", "command"], default="auto")
    r = sub.add_parser("record")
    r.add_argument("--key", required=True)
    r.add_argument("--write", required=True)
    r.add_argument("--version", type=int, required=True)
    r.add_argument("--link", required=True)
    a = ap.parse_args()
    return cmd_text(a) if a.cmd == "text" else cmd_record(a)


if __name__ == "__main__":
    sys.exit(main())
