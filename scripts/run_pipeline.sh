#!/usr/bin/env bash
# 증시추세분석 파이프라인 (GitHub Actions 러너 / Linux 기준)
# 사용법: run_pipeline.sh [기준일YYYYMMDD]   (생략 시 자동 계산)
# 동작:
#  1) 데이터 수집·계산 -> data/report_data_기준일.json 저장 (Claude가 1절 원인 문구 작성 시 참고)
#  2) narrative/기준일.json 이 없으면 여기서 종료(발행 안 함, 정상 종료)
#  3) 있으면 HTML -> PDF -> Google Drive 업로드 -> state/published/ 기록
# 발행은 날짜당 한 번만 한다. 재발행은 FORCE=1. 실패해도 자동 재시도하지 않는다.
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT/scripts"

read -r DATE WRITE PREV < <(python3 calc_dates.py "${1:-}")
echo "[run_pipeline] 기준일=$DATE 작성일=$WRITE 전일=$PREV"

echo "[1/5] 미국 데이터 (Yahoo Finance)"
python3 build_report.py "$DATE"

echo "[1-1/5] 국내 지수 (KRX pykrx)"
python3 build_krx_domestic.py "$DATE"

echo "[2/5] KRX 수급·시세 (pykrx)"
python3 build_krx.py "$DATE"
python3 build_krx.py "$PREV"

mkdir -p "$ROOT/data" "$ROOT/state/published" "$ROOT/out"
cp "report_data_${DATE}.json" "$ROOT/data/"

NARR="$ROOT/narrative/${DATE}.json"
if [ ! -f "$NARR" ]; then
  echo "[run_pipeline] narrative/${DATE}.json 없음 -> 데이터만 저장하고 종료 (발행 안 함)"
  exit 0
fi

shopt -s nullglob
PUBLISHED=("$ROOT/state/published/${DATE}"_v*.json)
if [ ${#PUBLISHED[@]} -gt 0 ] && [ "${FORCE:-0}" != "1" ]; then
  echo "[run_pipeline] ${DATE} 이미 발행됨(${#PUBLISHED[@]}건) -> 건너뜀"
  exit 0
fi
VER=$(( ${#PUBLISHED[@]} + 1 ))

echo "[3/5] HTML 생성"
python3 build_v3_html.py "$WRITE" "$DATE" "$PREV"
HTML="증시추세분석-${WRITE}-v2.html"

echo "[4/5] PDF 변환 (v${VER})"
PDF_NAME="증시추세분석 (${WRITE})_v${VER}.pdf"
"${CHROME_BIN:-google-chrome}" --headless=new --no-sandbox --disable-gpu \
  --no-pdf-header-footer --print-to-pdf="$ROOT/out/$PDF_NAME" \
  "file://$(pwd)/$HTML"

mkdir -p "$ROOT/reports"
cp "$HTML" "$ROOT/reports/${PDF_NAME%.pdf}.html"

echo "[5/5] Google Drive 업로드"
UP_OUT=$(python3 upload_pdf.py --file "$ROOT/out/$PDF_NAME" --title "$PDF_NAME" \
  --folder-id "${GDRIVE_FOLDER_ID:?GDRIVE_FOLDER_ID 필요}" --public)
echo "$UP_OUT"
FILE_ID=$(echo "$UP_OUT" | awk '/^id:/{print $2}')
LINK=$(echo "$UP_OUT" | awk '/^webViewLink:/{print $2}')
[ -n "$LINK" ] || { echo "Drive 링크를 받지 못함 -> 발행 기록 안 함"; exit 1; }

HTML_NAME="${PDF_NAME%.pdf}.html"
HTML_UP_OUT=$(python3 upload_pdf.py --file "$ROOT/reports/$HTML_NAME" --title "$HTML_NAME" \
  --folder-id "$GDRIVE_FOLDER_ID" --public)
echo "$HTML_UP_OUT"
HTML_FILE_ID=$(echo "$HTML_UP_OUT" | awk '/^id:/{print $2}')
HTML_LINK=$(echo "$HTML_UP_OUT" | awk '/^webViewLink:/{print $2}')
[ -n "$HTML_LINK" ] || { echo "HTML Drive 링크를 받지 못함 -> 발행 기록 안 함"; exit 1; }

cat > "$ROOT/state/published/${DATE}_v${VER}.json" <<JSON
{"date": "$DATE", "write_date": "$WRITE", "version": $VER, "pdf_name": "$PDF_NAME",
 "drive_file_id": "$FILE_ID", "webViewLink": "$LINK",
 "html_name": "$HTML_NAME", "html_drive_file_id": "$HTML_FILE_ID", "html_webViewLink": "$HTML_LINK",
 "published_at_utc": "$(date -u +%Y-%m-%dT%H:%M:%SZ)"}
JSON
echo "[run_pipeline] 발행 완료: $PDF_NAME  $LINK"
