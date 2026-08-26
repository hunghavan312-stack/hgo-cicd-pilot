#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
HGO.CICD.04.SYNC_TO_DRIVE — v0.2
Đồng bộ nội dung HGO lên HGO_ROOT trên Google Drive.

Nguyên Lý Bàn Tay + yêu cầu Gate (secrets_required: false):
  - MẶC ĐỊNH là chạy thử (dry-run): KHÔNG kết nối Drive, KHÔNG cần khóa,
    chỉ liệt kê các thao tác sẽ làm. An toàn tuyệt đối trong CI.
  - Biến HGO_DRIVE_DRY_RUN=true ép chạy thử kể cả khi có cờ --that.
  - Chỉ chạy thật khi: có cờ --that VÀ không bị ép dry-run VÀ đủ 2 biến
    GOOGLE_SERVICE_ACCOUNT_JSON + HGO_ROOT_FOLDER_ID.

Cách chạy:
  python scripts/sync_to_drive.py --source . --dry-run     # chạy thử
  python scripts/sync_to_drive.py --source . --that        # chạy thật
"""
import argparse, json, mimetypes, os, sys
from pathlib import Path

BO_QUA = {".git", ".github", "__pycache__", "reports"}

def liet_ke(goc: Path):
    for muc in sorted(goc.rglob("*")):
        if any(p in BO_QUA or p.startswith(".") for p in muc.relative_to(goc).parts):
            continue
        if muc.is_file():
            yield muc

def chay_thu(goc: Path) -> int:
    nhat_ky = [f"[ĐẨY LÊN] {f.relative_to(goc).as_posix()}" for f in liet_ke(goc)]
    print("=== Đồng bộ HGO lên Drive — chế độ: CHẠY THỬ (không ghi, không cần khóa) ===")
    [print("  " + d) for d in nhat_ky]
    print(f"=== Xong: {len(nhat_ky)} thao tác dự kiến, 0 thao tác ghi thật ===")
    return 0

def chay_that(goc: Path) -> int:
    try:
        from google.oauth2 import service_account
        from googleapiclient.discovery import build
        from googleapiclient.http import MediaFileUpload
    except ImportError:
        print("⚠ Thiếu thư viện: pip install google-api-python-client google-auth")
        return 1
    khoa, goc_id = os.environ.get("GOOGLE_SERVICE_ACCOUNT_JSON"), os.environ.get("HGO_ROOT_FOLDER_ID")
    if not khoa or not goc_id:
        print("⚠ Chạy thật cần GOOGLE_SERVICE_ACCOUNT_JSON và HGO_ROOT_FOLDER_ID.")
        return 1
    uq = service_account.Credentials.from_service_account_info(
        json.loads(khoa), scopes=["https://www.googleapis.com/auth/drive"])
    drive = build("drive", "v3", credentials=uq)
    bo_dem = {}
    def dam_bao_tm(duong: tuple) -> str:
        if duong in bo_dem:
            return bo_dem[duong]
        cha = goc_id if len(duong) == 1 else dam_bao_tm(duong[:-1])
        ten = duong[-1].replace("'", "\\'")
        q = (f"name='{ten}' and '{cha}' in parents and "
             "mimeType='application/vnd.google-apps.folder' and trashed=false")
        ds = drive.files().list(q=q, fields="files(id)", pageSize=1).execute().get("files", [])
        idm = ds[0]["id"] if ds else drive.files().create(body={
            "name": duong[-1], "mimeType": "application/vnd.google-apps.folder",
            "parents": [cha]}, fields="id").execute()["id"]
        bo_dem[duong] = idm
        return idm
    so = 0
    print("=== Đồng bộ HGO lên Drive — chế độ: CHẠY THẬT ===")
    for f in liet_ke(goc):
        rel = f.relative_to(goc)
        cha = goc_id if len(rel.parts) == 1 else dam_bao_tm(rel.parts[:-1])
        kieu = mimetypes.guess_type(f.name)[0] or "application/octet-stream"
        ten = f.name.replace("'", "\\'")
        q = (f"name='{ten}' and '{cha}' in parents and "
             "mimeType!='application/vnd.google-apps.folder' and trashed=false")
        ds = drive.files().list(q=q, fields="files(id)", pageSize=1).execute().get("files", [])
        media = MediaFileUpload(str(f), mimetype=kieu)
        if ds:
            drive.files().update(fileId=ds[0]["id"], media_body=media).execute()
            print(f"  [CẬP NHẬT] {rel.as_posix()}")
        else:
            drive.files().create(body={"name": f.name, "parents": [cha]},
                                 media_body=media, fields="id").execute()
            print(f"  [TẠO MỚI] {rel.as_posix()}")
        so += 1
    print(f"=== Xong: {so} thao tác ghi thật ===")
    return 0

def main() -> int:
    bd = argparse.ArgumentParser()
    bd.add_argument("--source", default=".")
    bd.add_argument("--dry-run", action="store_true", help="chạy thử (mặc định)")
    bd.add_argument("--that", action="store_true", help="chạy thật")
    ts = bd.parse_args()
    ep_thu = os.environ.get("HGO_DRIVE_DRY_RUN", "").lower() == "true"
    goc = Path(ts.source)
    if ts.that and not ts.dry_run and not ep_thu:
        return chay_that(goc)
    return chay_thu(goc)

if __name__ == "__main__":
    sys.exit(main())
