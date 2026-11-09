"""프로그램 파일(scripts/, .github/workflows/)을 드라이브 작업 폴더에 버전 폴더로 백업한다.

- 원본은 깃허브 저장소이고, 드라이브는 백업 사본이다.
- 버전 폴더: 작업 폴더 아래의 P1, P2, P3 … (이름이 P + 숫자인 폴더). 기존 버전은 덮어쓰지 않는다.
- 최신 버전 폴더와 내용(파일 이름과 md5 체크섬)이 같으면 아무것도 하지 않는다.
- 내용이 다르면 다음 번호 폴더(예: P3)를 만들고, 그 안에 소스/ 와 워크플로/ 를 만들어 파일을 올린다.
- 파일을 지우지 않는다. 비밀 정보가 들어갈 수 있는 파일(.env, secret, token, credential, 키 파일)은 올리지 않는다.

사용법:
  python3 upload_programs.py --folder-id <작업폴더ID> [--repo-root ..] [--dry-run]
"""
import argparse
import hashlib
import re
import sys
from pathlib import Path

_HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(_HERE))
from upload_pdf import get_service  # noqa: E402

FOLDER_MIME = "application/vnd.google-apps.folder"
SECRET_HINTS = (".env", "secret", "token", "credential", ".key", ".pem")
SOURCE_SUB = "소스"
WORKFLOW_SUB = "워크플로"
VERSION_RE = re.compile(r"^P(\d+)$")


def is_secret_like(name: str) -> bool:
    low = name.lower()
    return any(h in low for h in SECRET_HINTS)


def esc(s: str) -> str:
    return s.replace("\\", "\\\\").replace("'", "\\'")


def collect(repo_root: Path):
    """(폴더 이름, 로컬 파일 경로) 목록을 돌려준다."""
    items = []
    for p in sorted((repo_root / "scripts").iterdir()):
        if p.is_file() and not p.name.startswith(".") and not is_secret_like(p.name):
            items.append((SOURCE_SUB, p))
    wf_dir = repo_root / ".github" / "workflows"
    if wf_dir.exists():
        for p in sorted(wf_dir.iterdir()):
            if p.is_file() and p.suffix in (".yml", ".yaml") and not is_secret_like(p.name):
                items.append((WORKFLOW_SUB, p))
    return items


def md5_of(path: Path) -> str:
    h = hashlib.md5()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def list_children(service, parent_id: str, mime: str | None = None):
    q = f"'{parent_id}' in parents and trashed = false"
    if mime:
        q += f" and mimeType = '{mime}'"
    out, token = [], None
    while True:
        res = service.files().list(q=q, fields="nextPageToken, files(id,name,md5Checksum,mimeType)",
                                   pageSize=200, pageToken=token).execute()
        out.extend(res.get("files", []))
        token = res.get("nextPageToken")
        if not token:
            return out


def latest_version(service, parent_id: str):
    """(번호, 폴더 ID) 를 돌려준다. 버전 폴더가 없으면 (0, None)."""
    best = (0, None)
    for f in list_children(service, parent_id, FOLDER_MIME):
        m = VERSION_RE.match(f["name"])
        if m and int(m.group(1)) > best[0]:
            best = (int(m.group(1)), f["id"])
    return best


def snapshot_matches(service, version_id: str, items) -> bool:
    """버전 폴더의 파일 목록(이름과 md5)이 지금 로컬 파일과 같은지 확인한다."""
    remote = {}
    for sub in (SOURCE_SUB, WORKFLOW_SUB):
        sub_folders = [f for f in list_children(service, version_id, FOLDER_MIME) if f["name"] == sub]
        if not sub_folders:
            continue
        for f in list_children(service, sub_folders[0]["id"]):
            remote[(sub, f["name"])] = f.get("md5Checksum")
    local = {(sub, p.name): md5_of(p) for sub, p in items}
    return remote == local


def create_folder(service, name: str, parent_id: str) -> str:
    body = {"name": name, "mimeType": FOLDER_MIME, "parents": [parent_id]}
    return service.files().create(body=body, fields="id").execute()["id"]


def upload_new(service, path: Path, parent_id: str):
    from googleapiclient.http import MediaFileUpload
    media = MediaFileUpload(str(path), resumable=False)
    body = {"name": path.name, "parents": [parent_id]}
    service.files().create(body=body, media_body=media, fields="id").execute()


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--folder-id", required=True, help="드라이브 작업 폴더 ID")
    ap.add_argument("--repo-root", default=str(_HERE.parent))
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args()

    items = collect(Path(args.repo_root))
    if args.dry_run:
        for sub, p in items:
            print(f"[dry-run] {sub}/{p.name}")
        return 0

    service = get_service()
    num, latest_id = latest_version(service, args.folder_id)
    if latest_id and snapshot_matches(service, latest_id, items):
        print(f"변경 없음: 최신 버전 P{num}과 같다. 새 버전을 만들지 않는다.")
        return 0

    new_num = num + 1
    version_id = create_folder(service, f"P{new_num}", args.folder_id)
    sub_ids = {SOURCE_SUB: create_folder(service, SOURCE_SUB, version_id),
               WORKFLOW_SUB: create_folder(service, WORKFLOW_SUB, version_id)}
    failed = 0
    for sub, p in items:
        try:
            upload_new(service, p, sub_ids[sub])
            print(f"[올림] P{new_num}/{sub}/{p.name}")
        except Exception as e:  # 한 파일 실패가 나머지를 막지 않게 한다
            failed += 1
            print(f"[실패] {p.name}: {type(e).__name__}", file=sys.stderr)
    print(f"새 버전 P{new_num} 완료: 파일 {len(items)}개, 실패 {failed}개")
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
