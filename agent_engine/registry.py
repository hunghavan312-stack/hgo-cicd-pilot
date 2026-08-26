"""
registry.py
Agent Registry — nơi tra cứu Agent Card theo id.
"""

import json
from typing import Dict
from agent_card import AgentCard


class AgentRegistry:
    def __init__(self, config_path: str = "agents_config.json"):
        self.config_path = config_path
        self._agents: Dict[str, AgentCard] = {}
        self._load()

    def _load(self):
        with open(self.config_path, "r", encoding="utf-8") as f:
            data = json.load(f)
        for entry in data["agents"]:
            card = AgentCard.from_dict(entry)
            self._agents[card.id] = card

    def get(self, agent_id: str) -> AgentCard:
        if agent_id not in self._agents:
            raise KeyError(f"Không tìm thấy agent '{agent_id}' trong registry")
        return self._agents[agent_id]

    def list_agents(self):
        return list(self._agents.values())
