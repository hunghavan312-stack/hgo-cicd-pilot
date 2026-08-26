#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
run_ci_via_engine.py
Chạy trong workflow GitHub Actions, THAY cho việc gọi từng script CICD
trực tiếp. Gọi qua HGO Agent Engine để có:
  - Task log (agent_engine_task_log.json, upload làm artifact)
  - Tránh chạy lại Gate cho đúng commit SHA nếu workflow bị re-run
    (workflow_dispatch bấm lại, hoặc bước sau retry) — nhờ actions/cache
    khôi phục agent_engine_task_log.json theo key GITHUB_SHA.

Exit code: 0 nếu Gate PASSED, 1 nếu HOLD hoặc lỗi thật (để bước CI sau
biết dừng đúng chỗ, giữ đúng ý nghĩa "permissions: contents: read,
không tự sửa gì" của workflow gốc).
"""

import sys
import os
import json

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "agent_engine"))

from engine import AgentEngine  # noqa: E402


def main() -> int:
    repo_root = "."
    commit_sha = os.environ.get("GITHUB_SHA", "")
    if not commit_sha:
        print("⚠ Không có GITHUB_SHA (không chạy trong GitHub Actions?) — "
              "dùng hash nội dung thay thế, chậm hơn nhưng vẫn đúng.")

    engine = AgentEngine(
        config_path=os.path.join("agent_engine", "agents_config.json"),
        log_path="agent_engine_task_log.json",
    )

    dedup_key = commit_sha or None  # None -> engine tự tính hash_repo_content
    result = engine.run_gate(repo_root, dedup_key=dedup_key)

    print("=== Kết quả Gate qua Agent Engine ===")
    print(result["output"])

    if result["status"] == "failed":
        print("✗ Agent Engine báo crash thật khi chạy gate_runner.py:")
        print(result["output"])
        return 1

    # gate_runner.py tự ghi quyết định vào reports/test-results.json —
    # đọc lại để quyết định exit code CI, không suy đoán từ text log.
    results_path = os.path.join(repo_root, "reports", "test-results.json")
    if not os.path.exists(results_path):
        print(f"✗ Không tìm thấy {results_path} sau khi chạy Gate.")
        return 1

    with open(results_path, "r", encoding="utf-8") as f:
        test_results = json.load(f)

    decision = test_results.get("decision")
    print(f"[CI] Gate decision = {decision} "
          f"({test_results.get('tests_passed')}/{test_results.get('tests_total')} PASS)")

    return 0 if decision == "PASSED" else 1


if __name__ == "__main__":
    sys.exit(main())
