#!/usr/bin/env python3
"""예약 작업용 상태 판단 도구 (읽기 전용, 네트워크 없음).

저장소 루트에서 `git pull --rebase origin main` 직후 실행한다.
오늘 해야 할 다음 한 가지 일(state)을 JSON 한 줄로 알려 준다. 판단은 이 코드가 하고,
예약 작업(Claude)은 출력된 state에 맞는 일만 한다.

state 값
  TOO_EARLY       미국 정규장 마감 + 5분 전. 데이터를 만들면 장중 값이 들어간다. 기다린다.
  NEED_DATA       마감 후 확정 데이터가 없다. 데이터만 만드는 실행(workflow_dispatch, date만 전달)을 한다.
  NEED_NARRATIVE  확정 데이터가 있고 narrative가 없다. 원인 문구를 써서 push한다.
  WAIT_PUBLISH    narrative는 있고 발행 기록이 없다. 발행을 기다린다(최대 30분).
  NEED_KAKAO      발행됐고 같은 작성일 카톡 기록이 없다. 카톡 1회를 보내고 기록한다.
  DONE            발행과 카톡이 모두 끝났다. 아무것도 하지 않는다.
  STALE_NARRATIVE narrative는 있는데 데이터가 확정본이 아니다. 자동 처리하지 않고 사용자에게 보고한다.

사용: python3 scripts/routine_state.py [--date YYYYMMDD] [--now YYYY-MM-DDTHH:MM]   (--now는 KST, 시험용)
"""
import argparse
import datetime as dt
import glob
import json
import os
import subprocess
import sys
from zoneinfo import ZoneInfo

KST = ZoneInfo("Asia/Seoul")
ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
CLOSE_BUFFER = dt.time(6, 5)  # 미국 정규장 마감(겨울 06:00, 여름 05:00 KST) 뒤 5분 여유(겨울 기준으로 보수적)


def run(cmd):
    return subprocess.run(cmd, cwd=ROOT, capture_output=True, text=True, check=False).stdout.strip()


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--date", default="")
    ap.add_argument("--now", default="")
    a = ap.parse_args()

    now = dt.datetime.strptime(a.now, "%Y-%m-%dT%H:%M").replace(tzinfo=KST) if a.now else dt.datetime.now(KST)

    date, write, prev = run(["python3", "scripts/calc_dates.py", a.date]).split()
    write_d = dt.datetime.strptime(write, "%Y%m%d").date()
    key = f"{date}-w{write}" if write_d.isoweekday() == 1 else date

    base = dt.datetime.strptime(date, "%Y%m%d").date()
    close = dt.datetime.combine(base + dt.timedelta(days=1), CLOSE_BUFFER, tzinfo=KST)

    out = {
        "now_kst": now.strftime("%Y-%m-%d %H:%M"),
        "date": date, "write": write, "prev": prev, "key": key,
        "data_usable_from_kst": close.strftime("%Y-%m-%d %H:%M"),
    }

    # --- 데이터 확인: 파일 있음 + 미국 지수 날짜 == 기준일 + 마감 뒤에 만들어진 파일 ---
    data_path = f"data/report_data_{date}.json"
    data_ok, why = False, ""
    full = os.path.join(ROOT, data_path)
    if not os.path.exists(full):
        why = "데이터 파일 없음"
    else:
        try:
            idx = json.load(open(full, encoding="utf-8")).get("index_rows", {})
            us_dates = {v.get("date") for k, v in idx.items() if k in ("S&P 500", "나스닥 종합", "다우존스")}
            want = f"{date[:4]}-{date[4:6]}-{date[6:]}"
            ts = run(["git", "log", "-1", "--format=%cI", "--", data_path])
            made = dt.datetime.fromisoformat(ts).astimezone(KST) if ts else None
            if us_dates != {want}:
                why = f"미국 지수 날짜 {sorted(d for d in us_dates if d)} != 기준일 {want}"
            elif made is None:
                why = "데이터 파일이 저장소에 커밋되지 않음(생성 시각 확인 불가)"
            elif made < close:
                why = f"마감 전에 만든 데이터(생성 {made:%m-%d %H:%M} KST < {close:%m-%d %H:%M})"
            else:
                data_ok = True
                out["data_made_kst"] = made.strftime("%Y-%m-%d %H:%M")
        except Exception as e:  # 읽기 실패는 데이터 없음으로 본다
            why = f"데이터 파일 읽기 실패: {e}"
    out["data_ok"], out["data_reason"] = data_ok, why

    narrative = os.path.exists(os.path.join(ROOT, f"narrative/{key}.json"))
    pubs = sorted(glob.glob(os.path.join(ROOT, f"state/published/{key}_v*.json")),
                  key=lambda p: int(os.path.basename(p).rsplit("_v", 1)[1].split(".")[0]))
    out["narrative_exists"] = narrative
    out["published_version"] = int(os.path.basename(pubs[-1]).rsplit("_v", 1)[1].split(".")[0]) if pubs else 0
    out["published_link"] = json.load(open(pubs[-1], encoding="utf-8")).get("webViewLink", "") if pubs else ""

    kakao = {}
    try:
        kakao = json.loads(run(["python3", "scripts/kakao_message.py", "text", "--key", key, "--write", write, "--mode", "auto"]))
    except Exception:
        pass
    out["kakao_send"] = kakao.get("send")
    out["kakao_message"] = kakao.get("message", "")

    if now < close:
        state, todo = "TOO_EARLY", f"{close:%H:%M} KST 이후에 다시 실행한다. 지금 데이터를 만들지 않는다."
    elif pubs:
        if kakao.get("send") is False:
            state, todo = "DONE", "발행·카톡 모두 끝남. 아무것도 하지 않고 보고만 한다."
        else:
            state, todo = "NEED_KAKAO", "kakao_message_text 길이(200자 이하)를 확인하고 PlayMCP로 1회 보낸 뒤 record 한다."
    elif narrative:
        if data_ok:
            state, todo = "WAIT_PUBLISH", "narrative가 올라가 있다. 60초마다 pull하며 최대 30분 발행 기록을 기다린다."
        else:
            state, todo = "STALE_NARRATIVE", f"narrative는 있으나 데이터가 확정본이 아니다({why}). 자동 처리하지 않고 보고한다."
    elif data_ok:
        state, todo = "NEED_NARRATIVE", "data 파일의 숫자로 narrative를 쓰고 push한다."
    else:
        state, todo = "NEED_DATA", f"데이터만 만드는 실행을 한다({why}). 완료 후 다시 이 도구를 실행한다."
    out["state"], out["next_action"] = state, todo
    print(json.dumps(out, ensure_ascii=False))


if __name__ == "__main__":
    sys.exit(main())
