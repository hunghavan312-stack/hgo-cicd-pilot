"""
engine.py
AgentEngine — điểm vào chính của HGO.AGENT_ENGINE.00.
"""

import hashlib
import os

from registry import AgentRegistry
from task_store import TaskStore
from adapters import build_adapter


def hash_repo_content(repo_root: str) -> str:
    """Băm SHA-256 nội dung mọi file trong nodes/ và scripts/ (bỏ qua
    reports/, HGO_INDEX.md — vì đó là SẢN PHẨM sinh ra, không phải đầu vào).
    Dùng làm dedup_key khi không có git commit SHA sẵn (ví dụ chạy local).
    Trong CI, ưu tiên dùng GITHUB_SHA thay vì hàm này — rẻ hơn nhiều."""
    h = hashlib.sha256()
    watched_dirs = ["nodes", "scripts"]
    for d in watched_dirs:
        base = os.path.join(repo_root, d)
        if not os.path.isdir(base):
            continue
        for root, _, names in os.walk(base):
            for name in sorted(names):
                path = os.path.join(root, name)
                h.update(path.encode("utf-8"))
                with open(path, "rb") as f:
                    h.update(f.read())
    return h.hexdigest()


class AgentEngine:
    def __init__(
        self,
        config_path: str = "agents_config.json",
        log_path: str = "task_log.json",
    ):
        self.registry = AgentRegistry(config_path)
        self.store = TaskStore(log_path)

    def submit(self, agent_id: str, input_data: str, force: bool = False,
               dedup_key: str = None) -> dict:
        """Giao việc cho agent. Nếu việc y hệt đã làm rồi (và force=False),
        trả lại kết quả cũ, không chạy lại.

        dedup_key: khóa dùng để phát hiện trùng lặp, TÁCH RIÊNG khỏi input_data
        thật truyền cho script. Với agent nhận thẳng text làm input (ví dụ
        claude_writer), có thể bỏ qua — mặc định dùng input_data. Với agent
        kiểu "repo script" (input_data = đường dẫn thư mục, không đổi dù nội
        dung đổi), LUÔN truyền dedup_key = git SHA hoặc hash_repo_content(...),
        nếu không dedup sẽ trả nhầm kết quả cũ sau khi bạn sửa node."""

        if not force:
            existing = self.store.find_existing(agent_id, dedup_key if dedup_key is not None else input_data)
            if existing and existing["status"] == "completed":
                print(f"[ĐÃ CÓ KẾT QUẢ TRƯỚC ĐÓ — không gọi lại] task_id={existing['task_id']}")
                return existing
            if existing and existing["status"] == "working":
                print(f"[ĐANG XỬ LÝ RỒI — bỏ qua yêu cầu trùng] task_id={existing['task_id']}")
                return existing

        card = self.registry.get(agent_id)
        task = self.store.create(agent_id, input_data, dedup_input=dedup_key)
        self.store.update(task["task_id"], status="working")

        adapter = build_adapter(card)
        try:
            output = adapter.run(input_data)
            task = self.store.update(task["task_id"], status="completed", output=output)
        except Exception as e:
            task = self.store.update(task["task_id"], status="failed", output=str(e))

        return task

    def run_pipeline(self, repo_root: str, force: bool = False, dedup_key: str = None) -> list:
        """Chạy đúng thứ tự trong HGO.CICD.01.PIPELINE_CORE.CANONICAL.md (mục 3,
        Vòng 3 — SỬA): validate_nodes → build_index → check_index_links →
        sync_to_drive(dry-run).
        "Không thể kiểm tra một chỉ mục trước khi chỉ mục ấy được sinh ra."

        repo_root = đường dẫn gốc repo đích (phải chứa scripts/ và nodes/).
        dedup_key = khóa nội dung (git SHA hoặc hash_repo_content(repo_root)).
        Nếu không truyền, TỰ ĐỘNG tính bằng hash_repo_content — an toàn hơn
        mặc định cũ (băm theo đường dẫn), nhưng chậm hơn 1 SHA có sẵn.

        Dừng ngay nếu một bước bị status="failed" (script crash thật —
        có traceback). KHÔNG dừng nếu script chỉ trả exit_code != 0 (đó là
        PASS/FAIL hợp lệ của chính script) — trừ validate_nodes FAIL thì
        dừng vì bước sau cần chỉ mục sinh từ node đã qua kiểm tra."""

        if dedup_key is None:
            dedup_key = hash_repo_content(repo_root)

        steps = [
            "cicd_validate_nodes",
            "cicd_build_index",
            "cicd_check_index_links",
            "cicd_sync_to_drive",
        ]
        results = []
        for agent_id in steps:
            task = self.submit(agent_id, repo_root, force=force, dedup_key=f"{dedup_key}::{agent_id}")
            results.append(task)
            if task["status"] == "failed":
                print(f"[PIPELINE DỪNG] bước '{agent_id}' crash thật: {task['output']}")
                break
            if agent_id == "cicd_validate_nodes" and "[exit_code=1]" in task["output"]:
                print("[PIPELINE DỪNG] validate_nodes FAIL — không sinh chỉ mục từ node lỗi.")
                break
        return results

    def run_gate(self, repo_root: str, force: bool = False, dedup_key: str = None) -> dict:
        """Chạy toàn bộ Gate qua gate_runner.py thật (8 ca DR-01..DR-08).
        LƯU Ý: script này xóa và sinh lại reports/ + HGO_INDEX.md trong repo_root.

        dedup_key: nên truyền git SHA trong CI (rẻ, đáng tin cậy). Nếu để
        trống, tự tính hash_repo_content(repo_root)."""
        if dedup_key is None:
            dedup_key = hash_repo_content(repo_root)
        return self.submit("cicd_gate_runner", repo_root, force=force,
                            dedup_key=f"{dedup_key}::cicd_gate_runner")
