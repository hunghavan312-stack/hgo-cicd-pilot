"""
agent_card.py
Định nghĩa Agent Card — "danh thiếp" mô tả năng lực một agent,
theo tinh thần chuẩn A2A (Agent2Agent Protocol).
"""

from dataclasses import dataclass, field
from typing import List


@dataclass
class AgentCard:
    id: str                     # định danh duy nhất, ví dụ "claude_writer"
    name: str                   # tên hiển thị
    kind: str                   # "claude_api" | "python_script" | "mock"
    capabilities: List[str] = field(default_factory=list)  # ví dụ ["viết", "tóm tắt"]
    description: str = ""
    endpoint: str = ""          # với python_script: đường dẫn script TÍNH TỪ GỐC REPO đích
                                 # (repo_root truyền vào submit()); với claude_api: model id
    args: List[str] = field(default_factory=list)  # tham số dòng lệnh cố định, ví dụ
                                                     # ["--output", "HGO_INDEX.md"]

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "name": self.name,
            "kind": self.kind,
            "capabilities": self.capabilities,
            "description": self.description,
            "endpoint": self.endpoint,
            "args": self.args,
        }

    @staticmethod
    def from_dict(d: dict) -> "AgentCard":
        return AgentCard(
            id=d["id"],
            name=d.get("name", d["id"]),
            kind=d.get("kind", "mock"),
            capabilities=d.get("capabilities", []),
            description=d.get("description", ""),
            endpoint=d.get("endpoint", ""),
            args=d.get("args", []),
        )
