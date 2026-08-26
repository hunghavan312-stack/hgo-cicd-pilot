#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
HGO.CICD.03.BUILD_INDEX — v0.2
Sinh chỉ mục tổng HGO_INDEX.md từ toàn bộ node trong kho.
v0.2: BỎ dấu thời gian trong nội dung để bảo đảm tính tất định (DR-07):
      cùng đầu vào → cùng từng byte đầu ra; ngày tháng đã có trong git.
Cách chạy: python scripts/build_index.py . --output HGO_INDEX.md
"""
import argparse, re, sys
from pathlib import Path

def la_node(f: Path) -> bool:
    return ("nodes" in f.parts) or (f.stem.startswith("HGO.") and f.stem != "HGO_INDEX")

def trich(noi_dung: str, tieu_de: str) -> str:
    kq = re.search(rf"^##\s*{re.escape(tieu_de)}\s*\n+(.+)$", noi_dung, re.MULTILINE)
    return kq.group(1).strip() if kq else "(chưa ghi)"

def lay_domain(ten: str) -> str:
    p = ten.split(".")
    return p[1] if len(p) >= 3 and not p[1].isdigit() else "(RÚT GỌN)"

def main() -> int:
    bd = argparse.ArgumentParser()
    bd.add_argument("source", nargs="?", default=".")
    bd.add_argument("--output", default="HGO_INDEX.md")
    ts = bd.parse_args()
    goc, dich = Path(ts.source), Path(ts.output)
    theo_mien, so = {}, 0
    for f in sorted(goc.rglob("*.md")):
        if f.resolve() == dich.resolve() or not la_node(f):
            continue
        so += 1
        nd = f.read_text(encoding="utf-8", errors="replace")
        theo_mien.setdefault(lay_domain(f.stem), []).append({
            "ten": f.stem, "dd": f.as_posix(),
            "tt": trich(nd, "Trạng thái"), "mt": trich(nd, "Mục tiêu")})
    dong = ["# HGO_INDEX — Chỉ mục tổng hệ thống HưngGraph OS", "",
            f"Tổng số node: {so}", ""]
    for mien in sorted(theo_mien):
        dong += [f"## Miền: {mien} ({len(theo_mien[mien])} node)", ""]
        for m in theo_mien[mien]:
            dong += [f"### {m['ten']}", f"- Trạng thái: {m['tt']}",
                     f"- Mục tiêu: {m['mt']}", f"- File: `{m['dd']}`", ""]
    dich.parent.mkdir(parents=True, exist_ok=True)
    dich.write_text("\n".join(dong), encoding="utf-8")
    print(f"✓ Đã sinh chỉ mục {dich} — {so} node, {len(theo_mien)} miền.")
    return 0

if __name__ == "__main__":
    sys.exit(main())
