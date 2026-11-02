"""지침·컨텍스트·실행방법 최신 버전을 Drive 발행 폴더에 올린다.

- 대상: docs/ 안의 증시추세분석-클라우드-{지침,컨텍스트,실행방법}-vN.md 가운데 종류별 최신 번호 하나씩.
- 같은 이름의 파일이 발행 폴더에 이미 있으면 건너뛴다(중복 업로드 방지). 버전 번호가 바뀌면 이름이 달라서 새로 올라간다.
- 공유는 하지 않는다(비공개). 보고서 PDF의 --public 공유와는 별개다.

사용법:
  python3 upload_docs.py --folder-id <폴더ID> [--docs-dir ../docs] [--dry-run]
"""
import argparse
import re
import sys
from pathlib import Path

_HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(_HERE))
from upload_pdf import get_service, upload  # noqa: E402

PATTERN = re.compile(r"^증시추세분석-클라우드-(지침|컨텍스트|실행방법)-v(\d+)\.md$")


def latest_per_kind(docs_dir: Path) -> dict:
    best = {}
    for p in docs_dir.iterdir():
        m = PATTERN.match(p.name)
        if not m:
            continue
        kind, ver = m.group(1), int(m.group(2))
        if kind not in best or ver > best[kind][0]:
            best[kind] = (ver, p)
    return {k: v[1] for k, v in best.items()}


def exists_in_folder(service, name: str, folder_id: str) -> bool:
    safe = name.replace("\\", "\\\\").replace("'", "\\'")
    q = f"name = '{safe}' and '{folder_id}' in parents and trashed = false"
    res = service.files().list(q=q, fields="files(id,name)", pageSize=5).execute()
    return bool(res.get("files"))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--docs-dir", default=str(_HERE.parent / "docs"))
    ap.add_argument("--folder-id", default=None)
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args()

    targets = latest_per_kind(Path(args.docs_dir))
    if not targets:
        print("올릴 문서가 없음(docs/ 확인)")
        return 1
    if args.dry_run or not args.folder_id:
        for kind, p in sorted(targets.items()):
            print(f"[dry-run] {kind}: {p.name}")
        return 0

    service = get_service()
    for kind, p in sorted(targets.items()):
        if exists_in_folder(service, p.name, args.folder_id):
            print(f"[건너뜀] 이미 있음: {p.name}")
            continue
        r = upload(str(p), p.name, public=False, folder_id=args.folder_id)
        print(f"[업로드] {p.name} id={r.get('id')} link={r.get('webViewLink')}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
