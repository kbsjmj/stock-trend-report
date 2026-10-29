#!/usr/bin/env bash
# 수정된 보고서 HTML을 새 버전으로 저장한다: PDF 생성 -> Drive 업로드(HTML·PDF) -> reports/ 커밋 -> state 기록.
# 사용: save_report_version.sh <원본 HTML(reports/ 안)> <DATE 기준일> <WRITE 작성일> <VER 버전>
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
SRC="$1"; DATE="$2"; WRITE="$3"; VER="$4"
BASE="증시추세분석 (${WRITE})_v${VER}"
PDF_NAME="${BASE}.pdf"; HTML_NAME="${BASE}.html"

mkdir -p "$ROOT/out" "$ROOT/state/published"
cp "$ROOT/reports/$SRC" "$ROOT/reports/$HTML_NAME"
cp "$ROOT/reports/$HTML_NAME" "$ROOT/out/$HTML_NAME"
"${CHROME_BIN:-google-chrome}" --headless=new --no-sandbox --disable-gpu \
  --no-pdf-header-footer --print-to-pdf="$ROOT/out/$PDF_NAME" "file://$ROOT/out/$HTML_NAME"
cp "$ROOT/out/$PDF_NAME" "$ROOT/reports/$PDF_NAME"

cd "$ROOT/scripts"
PDF_UP=$(python3 upload_pdf.py --file "$ROOT/out/$PDF_NAME" --title "$PDF_NAME" --folder-id "${GDRIVE_FOLDER_ID:?GDRIVE_FOLDER_ID 필요}" --public)
HTML_UP=$(python3 upload_pdf.py --file "$ROOT/out/$HTML_NAME" --title "$HTML_NAME" --folder-id "$GDRIVE_FOLDER_ID" --public)
echo "$PDF_UP"; echo "$HTML_UP"
PDF_ID=$(echo "$PDF_UP" | awk '/^id:/{print $2}'); PDF_LINK=$(echo "$PDF_UP" | awk '/^webViewLink:/{print $2}')
HTML_ID=$(echo "$HTML_UP" | awk '/^id:/{print $2}'); HTML_LINK=$(echo "$HTML_UP" | awk '/^webViewLink:/{print $2}')
[ -n "$PDF_LINK" ] && [ -n "$HTML_LINK" ] || { echo "Drive 링크를 받지 못함 -> 기록 안 함"; exit 1; }

cat > "$ROOT/state/published/${DATE}_v${VER}.json" <<JSON
{"date": "$DATE", "write_date": "$WRITE", "version": $VER, "pdf_name": "$PDF_NAME",
 "drive_file_id": "$PDF_ID", "webViewLink": "$PDF_LINK",
 "html_name": "$HTML_NAME", "html_drive_file_id": "$HTML_ID", "html_webViewLink": "$HTML_LINK",
 "note": "수동 수정본(5-2 국내 테마 정렬, 요인 색·쪽 번호 점선 반영)",
 "published_at_utc": "$(date -u +%Y-%m-%dT%H:%M:%SZ)"}
JSON
echo "[save_report_version] 저장 완료: $PDF_NAME $PDF_LINK"
