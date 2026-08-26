"""
task_store.py
Lưu trữ Task theo tinh thần A2A (Task ID, trạng thái submitted/working/completed/failed)
và cơ chế "tránh nhắc lại": băm theo NỘI DUNG (dedup_key), không phải theo
tham số truyền cho script.

LƯU Ý QUAN TRỌNG (đã sửa lỗi thiết kế): với các agent kiểu "repo script"
(validate_nodes, build_index, ...), input truyền cho adapter luôn là ĐƯỜNG
DẪN thư mục (ví dụ "pilot_repo") — đường dẫn này KHÔNG đổi dù nội dung file
bên trong đổi. Nếu băm theo input_data như bản đầu, dedup sẽ trả nhầm kết
quả cũ sau khi bạn đã sửa node. Vì vậy TaskStore giờ nhận thêm dedup_key
tùy chọn: nếu có, băm theo dedup_key (ví dụ git commit SHA, hoặc SHA-256
nội dung thư mục); nếu không có, mặc định băm theo input_data như cũ
(phù hợp với agent nhận thẳng text làm input, ví dụ claude_writer)."""

import json
import hashlib
import uuid
import os
from datetime import datetime, timezone
from typing import Optional, Dict, Any


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _hash_task(agent_id: str, dedup_input: str) -> str:
    raw = f"{agent_id}::{dedup_input}".encode("utf-8")
    return hashlib.sha256(raw).hexdigest()


class TaskStore:
    def __init__(self, log_path: str = "task_log.json"):
        self.log_path = log_path
        self._tasks: Dict[str, dict] = {}
        self._load()

    def _load(self):
        if os.path.exists(self.log_path):
            with open(self.log_path, "r", encoding="utf-8") as f:
                self._tasks = json.load(f)

    def _save(self):
        os.makedirs(os.path.dirname(self.log_path) or ".", exist_ok=True)
        with open(self.log_path, "w", encoding="utf-8") as f:
            json.dump(self._tasks, f, ensure_ascii=False, indent=2)

    def find_existing(self, agent_id: str, dedup_input: str) -> Optional[dict]:
        """Trả về Task đã tồn tại cùng dedup_input (nếu có), để tránh chạy lại."""
        h = _hash_task(agent_id, dedup_input)
        for task in self._tasks.values():
            if task["content_hash"] == h and task["status"] in ("completed", "working"):
                return task
        return None

    def create(self, agent_id: str, input_data: str, dedup_input: Optional[str] = None) -> dict:
        task_id = str(uuid.uuid4())
        key = dedup_input if dedup_input is not None else input_data
        task = {
            "task_id": task_id,
            "agent_id": agent_id,
            "content_hash": _hash_task(agent_id, key),
            "input": input_data,
            "dedup_key": key,
            "output": None,
            "status": "submitted",
            "created_at": _now(),
            "updated_at": _now(),
        }
        self._tasks[task_id] = task
        self._save()
        return task

    def update(self, task_id: str, status: str, output: Any = None):
        task = self._tasks[task_id]
        task["status"] = status
        task["updated_at"] = _now()
        if output is not None:
            task["output"] = output
        self._save()
        return task
