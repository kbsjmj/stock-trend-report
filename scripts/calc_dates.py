"""기준일(DATE), 작성일(WRITE), 전일(PREV)을 계산한다 (KST 기준).
규칙: 16시 이전이면 전 영업일을 기준일로, 16시 이후면 당일. 작성일 = 기준일 + 1일(달력).
예외(v47): 월요일 오전(16시 이전) 자동 실행은 작성일을 오늘(월요일)로 하고 기준일은 직전 금요일로 한다.
전일 = 기준일 직전 평일. 공휴일은 반영하지 않으므로 필요하면 인자로 직접 넘긴다.
사용: python3 calc_dates.py [기준일YYYYMMDD]  -> 'DATE WRITE PREV' 출력
"""
import datetime as dt
import sys
from zoneinfo import ZoneInfo


def last_weekday(d):
    while d.weekday() >= 5:
        d -= dt.timedelta(days=1)
    return d


def main():
    if len(sys.argv) > 1 and sys.argv[1]:
        date = dt.datetime.strptime(sys.argv[1], "%Y%m%d").date()
        write = date + dt.timedelta(days=1)
    else:
        now = dt.datetime.now(ZoneInfo("Asia/Seoul"))
        base = now.date() if now.hour >= 16 else now.date() - dt.timedelta(days=1)
        date = last_weekday(base)
        if now.weekday() == 0 and now.hour < 16:
            write = now.date()  # 월요일 보고서
        else:
            write = date + dt.timedelta(days=1)
    prev = last_weekday(date - dt.timedelta(days=1))
    f = "%Y%m%d"
    print(date.strftime(f), write.strftime(f), prev.strftime(f))


if __name__ == "__main__":
    main()
