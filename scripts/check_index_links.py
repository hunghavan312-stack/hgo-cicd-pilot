#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
HGO.CICD.05.CHECK_INDEX_LINKS — v0.2
Soát: (1) liên kết gãy trong chỉ mục, (2) node mồ côi, (3) liên kết nội bộ gãy.
Cách chạy: python scripts/check_index_links.py . --index HGO_INDEX.md
"""
import argparse, re, sys
from pathlib import Path

MAU_FILE = re.compile(r"`([^`\n]+?\.md)`")
MAU_LK = re.compile(r"\[[^\]]*\]\(([^)\s]+?\.md)\)")

def la_node(f: Path) -> bool:
    return ("nodes" in f.parts) or (f.stem.startswith("HGO.") and f.stem != "HGO_INDEX")

def main() -> int:
    bd = argparse.ArgumentParser()
    bd.add_argument("source", nargs="?", default=".")
    bd.add_argument("--index", default="HGO_INDEX.md")
    ts = bd.parse_args()
    goc, f_index = Path(ts.source), Path(ts.index)
    if not f_index.exists():
        print(f"✗ FAIL — không tìm thấy chỉ mục: {f_index} (chạy build_index trước).")
        return 1
    loi = []
    trong_index = set(MAU_FILE.findall(f_index.read_text(encoding="utf-8", errors="replace")))
    for dd in sorted(trong_index):
        if not Path(dd).exists():
            loi.append(f"[LIÊN KẾT GÃY] Chỉ mục ghi `{dd}` nhưng file không có.")
    node_dia = [f for f in sorted(goc.rglob("*.md")) if la_node(f)]
    for f in node_dia:
        if f.as_posix() not in trong_index:
            loi.append(f"[NODE MỒ CÔI] `{f.as_posix()}` chưa có trong chỉ mục.")
        for lk in MAU_LK.findall(f.read_text(encoding="utf-8", errors="replace")):
            if lk.startswith(("http://", "https://")):
                continue
            if not (f.parent / lk).resolve().exists():
                loi.append(f"[LIÊN KẾT NGOÀI GÃY] Trong `{f.as_posix()}` trỏ tới `{lk}` không tồn tại.")
    print(f"Đã soát: {len(trong_index)} đường dẫn trong chỉ mục, {len(node_dia)} node trên đĩa.")
    if loi:
        print(f"\n✗ FAIL — {len(loi)} lỗi:")
        [print("  " + d) for d in loi]
        return 1
    print("✓ PASS — chỉ mục và kho node khớp nhau hoàn toàn.")
    return 0

if __name__ == "__main__":
    sys.exit(main())
