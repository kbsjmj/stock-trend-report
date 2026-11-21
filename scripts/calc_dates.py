"""기준일(DATE), 작성일(WRITE), 전일(PREV)을 계산한다 (KST 기준).
규칙: 16시 이전이면 전 영업일을 기준일로, 16시 이후면 당일.
작성일 = 기준일 + 1일(달력). 토요일은 작성일이 될 수 있다(금요일 마감 데이터로 토요일 보고서를 낸다). 일요일이면 다음 월요일로 한다.
예외(v47): 월요일 오전(16시 이전) 자동 실행은 작성일을 오늘(월요일)로 하고 기준일은 직전 금요일로 한다.
전일 = 기준일 직전 평일. 공휴일은 반영하지 않으므로 필요하면 인자로 직접 넘긴다.
사용: python3 calc_dates.py [기준일YYYYMMDD] [--now YYYY-MM-DDTHH:MM]  -> 'DATE WRITE PREV' 출력
  --now는 KST 기준 시각(시험용). 기준일 인자가 있으면 --now는 무시된다.
"""
import datetime as dt
import sys
from zoneinfo import ZoneInfo

KST = ZoneInfo("Asia/Seoul")


def last_weekday(d):
    while d.weekday() >= 5:
        d -= dt.timedelta(days=1)
    return d


def next_weekday(d):
    while d.weekday() >= 5:
        d += dt.timedelta(days=1)
    return d


def write_after(d):
    """기준일 d의 작성일: 다음 날. 일요일이면 다음 월요일(토요일은 작성일로 허용)."""
    w = d + dt.timedelta(days=1)
    if w.weekday() == 6:
        w += dt.timedelta(days=1)
    return w


def main():
    args = sys.argv[1:]
    now_arg = ""
    if "--now" in args:
        i = args.index("--now")
        now_arg = args[i + 1] if i + 1 < len(args) else ""
        del args[i:i + 2]
    date_arg = args[0] if args else ""

    if date_arg:
        date = dt.datetime.strptime(date_arg, "%Y%m%d").date()
        write = write_after(date)
    else:
        now = dt.datetime.strptime(now_arg, "%Y-%m-%dT%H:%M").replace(tzinfo=KST) if now_arg else dt.datetime.now(KST)
        base = now.date() if now.hour >= 16 else now.date() - dt.timedelta(days=1)
        date = last_weekday(base)
        if now.weekday() == 0 and now.hour < 16:
            write = now.date()  # 월요일 보고서
        else:
            write = write_after(date)
    prev = last_weekday(date - dt.timedelta(days=1))
    f = "%Y%m%d"
    print(date.strftime(f), write.strftime(f), prev.strftime(f))


if __name__ == "__main__":
    main()
