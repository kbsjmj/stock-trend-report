"""Google Drive 업로드 공용 Tool.
로컬 파일을 디스크에서 직접 읽어 Drive REST API로 올린다(모델 컨텍스트를 거치지 않음 — 큰 파일도 문제없음).
인증은 이 폴더의 secrets/ 안에 있는 OAuth 토큰을 사용한다 (증시추세분석 전용 복사본).

사용법:
  python3 upload_pdf.py --file "<경로>" --title "<Drive에 표시할 이름>" [--public]

옵션:
  --public  권한을 '링크가 있는 사람은 볼 수 있음'으로 설정한다 (기본은 비공개, 업로더 본인만 접근).
            카카오톡 등 외부로 링크를 보낼 때만 쓴다. 공유 권한 변경은 되돌릴 수 있는 작업이지만
            외부 노출이므로, 이 스크립트를 자동 실행하는 쪽(run_report.sh 등)에서
            --public을 쓸지는 매번 의식적으로 결정한다.

필요 조건:
  - google-auth, google-auth-oauthlib, google-api-python-client (pip install google-api-python-client google-auth-httplib2 google-auth-oauthlib)
  - 토큰: 기본값은 secrets/token.json, secrets/credentials.json (이 파일 기준 상대 경로).
    GDRIVE_TOKEN / GDRIVE_CREDENTIALS 환경변수로 다른 경로를 지정할 수 있다.
  - 토큰이 만료되었고 refresh_token도 없으면 브라우저 인증이 필요하다. 이 경우
    credentials.json이 있는 쪽에서 한 번 다시 로그인해야 한다(자동화 불가, 사람이 해야 함).
"""
import argparse
import mimetypes
import os
import sys
from pathlib import Path

SCOPES = ["https://www.googleapis.com/auth/drive"]
_HERE = Path(__file__).resolve().parent
DEFAULT_TOKEN = str(_HERE / "secrets" / "token.json")
DEFAULT_CREDS = str(_HERE / "secrets" / "credentials.json")


def get_service():
    from google.oauth2.credentials import Credentials
    from google.auth.transport.requests import Request
    from google_auth_oauthlib.flow import InstalledAppFlow
    from googleapiclient.discovery import build

    token_path = Path(os.environ.get("GDRIVE_TOKEN", DEFAULT_TOKEN))
    creds_path = Path(os.environ.get("GDRIVE_CREDENTIALS", DEFAULT_CREDS))

    creds = None
    if token_path.exists():
        creds = Credentials.from_authorized_user_file(str(token_path), SCOPES)

    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            if not creds_path.exists():
                print(f"인증 정보가 없습니다: {creds_path}", file=sys.stderr)
                sys.exit(1)
            flow = InstalledAppFlow.from_client_secrets_file(str(creds_path), SCOPES)
            creds = flow.run_local_server(port=0)  # 브라우저 인증 필요 (자동화 환경에서는 실패)
        token_path.write_text(creds.to_json(), encoding="utf-8")

    return build("drive", "v3", credentials=creds, cache_discovery=False)


def upload(file_path: str, title: str, public: bool, folder_id: str | None = None):
    from googleapiclient.http import MediaFileUpload

    service = get_service()
    mime, _ = mimetypes.guess_type(file_path)
    mime = mime or "application/octet-stream"

    body = {"name": title}
    if folder_id:
        body["parents"] = [folder_id]

    media = MediaFileUpload(file_path, mimetype=mime, resumable=False)
    f = service.files().create(body=body, media_body=media, fields="id,webViewLink,webContentLink").execute()
    file_id = f["id"]

    if public:
        service.permissions().create(fileId=file_id, body={"type": "anyone", "role": "reader"}).execute()

    f = service.files().get(fileId=file_id, fields="id,webViewLink,webContentLink,size,name").execute()
    return f


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--file", required=True)
    ap.add_argument("--title", required=True)
    ap.add_argument("--folder-id", default=None)
    ap.add_argument("--public", action="store_true")
    args = ap.parse_args()

    if not Path(args.file).exists():
        print(f"파일 없음: {args.file}", file=sys.stderr)
        sys.exit(1)

    result = upload(args.file, args.title, args.public, args.folder_id)
    print("id:", result.get("id"))
    print("name:", result.get("name"))
    print("size:", result.get("size"))
    print("webViewLink:", result.get("webViewLink"))
    print("public:", args.public)
