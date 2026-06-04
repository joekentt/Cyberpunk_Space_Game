"""
ProgressionManager — rastreia o progresso rumo à condição de vitória.

Condição de vitória (Ciclo E): completar WIN_BOUNTY_COUNT missões BOUNTY.
Quando atingida, emite GAME_COMPLETED uma única vez.

Persiste via get_save_data / load_save_data (integra no payload v2 do serializer).
"""
from core.event_bus import bus

WIN_BOUNTY_COUNT = 5


class ProgressionManager:
    def __init__(self):
        self.bounties_completed: int = 0
        self.game_completed: bool = False
        bus.subscribe("MISSION_COMPLETED", self._on_mission_completed)

    def _on_mission_completed(self, data: dict):
        if self.game_completed:
            return
        if data.get("type") == "BOUNTY":
            self.bounties_completed += 1
            if self.bounties_completed >= WIN_BOUNTY_COUNT:
                self.game_completed = True
                bus.emit("GAME_COMPLETED", {
                    "bounties_completed": self.bounties_completed,
                })

    def get_save_data(self) -> dict:
        return {
            "bounties_completed": self.bounties_completed,
            "game_completed": self.game_completed,
        }

    def load_save_data(self, data: dict):
        self.bounties_completed = int(data.get("bounties_completed", 0))
        self.game_completed = bool(data.get("game_completed", False))
