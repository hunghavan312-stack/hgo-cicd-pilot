#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
HGO.CICD.02.VALIDATE_NODES — v0.2
Soát tên node theo chuẩn HGO.[DOMAIN].[SỐ].[CHỨC NĂNG] và các phần bắt buộc.
Quy tắc chọn file:
  - Mọi file .md nằm trong thư mục nodes/ BẮT BUỘC phải là node hợp lệ.
  - File .md ở nơi khác chỉ bị soát nếu tên bắt đầu bằng "HGO."
  - README, HGO_INDEX và tài liệu thường được bỏ qua.
Cách chạy: python scripts/validate_nodes.py .
"""
import re, sys
from pathlib import Path

MAU_DAY_DU = re.compile(r"^HGO\.[A-ZĐÀ-Ỹ_-]+\.\d+(\.[A-ZĐÀ-Ỹ0-9_.-]+)+$", re.UNICODE)
MAU_RUT_GON = re.compile(r"^HGO\.\d+(\.[A-ZĐÀ-Ỹ0-9_.-]+)+$", re.UNICODE)
PHAN_BAT_BUOC = ["# HGO", "## Mục tiêu", "## Trạng thái"]

def la_doi_tuong_soat(f: Path) -> bool:
    if "nodes" in f.parts:
        return True
    return f.stem.startswith("HGO.") and f.stem != "HGO_INDEX"

def kiem_tra_ten(ten: str) -> bool:
    return bool(MAU_DAY_DU.match(ten) or MAU_RUT_GON.match(ten))

def main() -> int:
    goc = Path(sys.argv[1]) if len(sys.argv) > 1 else Path(".")
    loi, so_file = [], 0
    for f in sorted(goc.rglob("*.md")):
        if not la_doi_tuong_soat(f):
            continue
        so_file += 1
        if not kiem_tra_ten(f.stem):
            loi.append(f"[TÊN SAI CHUẨN] {f}")
        noi_dung = f.read_text(encoding="utf-8", errors="replace")
        for p in PHAN_BAT_BUOC:
            if p not in noi_dung:
                loi.append(f"[THIẾU PHẦN '{p}'] {f}")
    print(f"Đã kiểm tra {so_file} file node.")
    if loi:
        print(f"\n✗ FAIL — {len(loi)} lỗi:")
        [print("  " + d) for d in loi]
        return 1
    print("✓ PASS — toàn bộ node đúng chuẩn HGO.")
    return 0

if __name__ == "__main__":
    sys.exit(main())
