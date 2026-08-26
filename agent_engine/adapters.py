"""
adapters.py
Mỗi adapter biết cách "chạy" một loại agent thật.
Engine không cần biết bên trong — chỉ gọi adapter.run(input_data).

QUAN TRỌNG: các script CICD thật (validate_nodes.py, build_index.py,
check_index_links.py, sync_to_drive.py, gate_runner.py) in TEXT THƯỜNG
ra stdout (có ✓/✗ PASS/FAIL bằng tiếng Việt), KHÔNG PHẢI JSON — khác với
bản dàn dựng trước đó của Claude. Chúng cũng giả định chạy với
cwd = gốc repo đích (nơi có thư mục scripts/ và nodes/), đúng như cách
gate_runner.py và workflow GitHub Actions thật gọi chúng.

Vì vậy input_data cho các agent CICD LUÔN LÀ đường dẫn tới GỐC REPO đích
(ví dụ "pilot_repo"), không phải đường dẫn tới 1 file/thư mục node lẻ.
"""

import os
import subprocess
from agent_card import AgentCard

TRACEBACK_MARKER = "Traceback (most recent call last)"


class MockAdapter:
    """Agent giả lập — dùng để chạy thử engine mà không cần API key."""

    def __init__(self, card: AgentCard):
        self.card = card

    def run(self, input_data: str) -> str:
        return f"[MOCK:{self.card.id}] đã xử lý: {input_data}"


class ClaudeAdapter:
    """Gọi Claude qua Anthropic API. Cần: pip install anthropic
    và biến môi trường ANTHROPIC_API_KEY."""

    def __init__(self, card: AgentCard):
        self.card = card
        self.model = card.endpoint or "claude-sonnet-4-6"

    def run(self, input_data: str) -> str:
        try:
            import anthropic
        except ImportError as e:
            raise RuntimeError(
                "Chưa cài thư viện anthropic. Chạy: pip install anthropic"
            ) from e

        api_key = os.environ.get("ANTHROPIC_API_KEY")
        if not api_key:
            raise RuntimeError("Chưa đặt biến môi trường ANTHROPIC_API_KEY")

        client = anthropic.Anthropic(api_key=api_key)
        response = client.messages.create(
            model=self.model,
            max_tokens=1024,
            messages=[{"role": "user", "content": input_data}],
        )
        return "".join(
            block.text for block in response.content if block.type == "text"
        )


class RepoScriptAdapter:
    """Adapter dùng chung cho các script CICD thật.

    input_data = đường dẫn GỐC REPO đích (chứa scripts/, nodes/, ...).
    card.endpoint = đường dẫn script TÍNH TỪ GỐC REPO đó, ví dụ
        "scripts/validate_nodes.py"
    card.args = tham số dòng lệnh cố định, ví dụ
        ["--output", "HGO_INDEX.md"]

    Script chạy với cwd=input_data (đúng như cách gate_runner.py và
    GitHub Actions gọi chúng: "python scripts/validate_nodes.py .").

    Phân biệt "crash thật" vs "tìm thấy vấn đề":
      - exit code khác 0 NHƯNG không có traceback -> vẫn coi là hoàn thành,
        trả về text kèm exit code, để pipeline biết PASS/FAIL/HOLD mà không
        raise lỗi giả (đúng ý nghĩa PASS/FAIL của các script này).
      - Có "Traceback (most recent call last)" trong output -> raise
        RuntimeError thật (script tự nó lỗi, không phải "báo cáo FAIL")."""

    ok_source_arg = "."  # mọi script thật đều nhận "." vì đã cwd=repo_root

    def __init__(self, card: AgentCard):
        self.card = card
        self.script_rel = card.endpoint
        self.fixed_args = list(card.args)

    def build_argv(self) -> list:
        return [self.ok_source_arg] + self.fixed_args

    def run(self, repo_root: str) -> str:
        script_abs = os.path.join(repo_root, self.script_rel)
        if not os.path.exists(script_abs):
            raise RuntimeError(f"Không tìm thấy script trong repo đích: {self.script_rel}")

        result = subprocess.run(
            ["python3", self.script_rel] + self.build_argv(),
            cwd=repo_root,
            capture_output=True,
            text=True,
            timeout=120,
        )
        combined = (result.stdout or "") + (result.stderr or "")

        if TRACEBACK_MARKER in combined:
            raise RuntimeError(f"Script crash thật (traceback):\n{combined}")

        return f"[exit_code={result.returncode}]\n{combined.strip()}"


class SyncToDriveAdapter(RepoScriptAdapter):
    """Adapter riêng cho sync_to_drive.py.

    AN TOÀN TUYỆT ĐỐI: LUÔN LUÔN chạy với --dry-run, KHÔNG BAO GIỜ tự
    thêm cờ --that — kể cả nếu ai đó lỡ ghi --that vào agents_config.json,
    adapter này bỏ qua nó. Ghi thật lên Drive phải là một hành động
    RIÊNG, người dùng chủ động gọi ngoài luồng Engine tự động.
    Đúng nguyên tắc gốc trong sync_to_drive.py: "MẶC ĐỊNH là dry-run"."""

    def build_argv(self) -> list:
        return ["--source", ".", "--dry-run"]  # cố định — bỏ qua card.args


def build_adapter(card: AgentCard):
    """Chọn đúng adapter theo 'kind' và capability khai báo trong Agent Card."""
    if card.kind == "claude_api":
        return ClaudeAdapter(card)
    if card.kind == "python_script":
        if "sync_drive" in card.capabilities:
            return SyncToDriveAdapter(card)
        return RepoScriptAdapter(card)
    return MockAdapter(card)
