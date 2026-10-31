#!/usr/bin/env bash
# 공식 보고서 PDF를 새 버전으로 저장한다: Drive 업로드(PDF만) -> reports/ 확인 -> state 기록.
# HTML은 만들지도 올리지도 않는다(보고서 HTML 금지).
# 사용: save_report_version.sh <reports/ 안의 PDF 파일명> <DATE 기준일> <WRITE 작성일> <VER 상태 버전> [Drive 제목]
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
SRC="$1"; DATE="$2"; WRITE="$3"; VER="$4"; TITLE="${5:-}"
case "$SRC" in *.pdf) ;; *) echo "PDF 파일만 받는다: $SRC"; exit 1 ;; esac
[ -f "$ROOT/reports/$SRC" ] || { echo "reports/에 없음: $SRC"; exit 1; }
PDF_NAME="${TITLE:-증시추세분석 (${WRITE})-v${VER}.pdf}"
case "$PDF_NAME" in *.pdf) ;; *) echo "제목은 .pdf로 끝나야 함: $PDF_NAME"; exit 1 ;; esac
if [ "$SRC" != "$PDF_NAME" ]; then cp "$ROOT/reports/$SRC" "$ROOT/reports/$PDF_NAME"; fi

mkdir -p "$ROOT/state/published"
cd "$ROOT/scripts"
PDF_UP=$(python3 upload_pdf.py --file "$ROOT/reports/$PDF_NAME" --title "$PDF_NAME" --folder-id "${GDRIVE_FOLDER_ID:?GDRIVE_FOLDER_ID 필요}" --public)
echo "$PDF_UP"
PDF_ID=$(echo "$PDF_UP" | awk '/^id:/{print $2}'); PDF_LINK=$(echo "$PDF_UP" | awk '/^webViewLink:/{print $2}')
[ -n "$PDF_LINK" ] || { echo "Drive 링크를 받지 못함 -> 기록 안 함"; exit 1; }

cat > "$ROOT/state/published/${DATE}_v${VER}.json" <<JSON
{"date": "$DATE", "write_date": "$WRITE", "version": $VER, "pdf_name": "$PDF_NAME",
 "drive_file_id": "$PDF_ID", "webViewLink": "$PDF_LINK",
 "note": "공식본 PDF 직접 업로드(HTML 없음)",
 "published_at_utc": "$(date -u +%Y-%m-%dT%H:%M:%SZ)"}
JSON
echo "[save_report_version] 저장 완료: $PDF_NAME $PDF_LINK"
