from dataclasses import dataclass, field
from typing import Dict, Any, List
from enum import Enum

class MissionStatus(Enum):
    AVAILABLE = "AVAILABLE"
    ACTIVE = "ACTIVE"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"
    ABANDONED = "ABANDONED"

@dataclass
class Mission:
    """
    Representa uma missão procedural no universo.
    """
    id: str
    title: str
    description: str
    type: str  # BOUNTY, COURIER, MINING, TRADE
    faction: str
    reward_credits: int
    reputation_impact: Dict[str, int] # Ex: {"Humans": 5, "Pirates": -10}
    
    # Objetivos e Progresso
    objectives: List[Dict[str, Any]] = field(default_factory=list)
    status: MissionStatus = MissionStatus.AVAILABLE
    
    # Metadados procedurais
    target_system: str = ""
    target_entity_id: str = ""

    # Progresso de kills (para missões BOUNTY)
    kill_progress: int = 0

    def to_dict(self) -> Dict[str, Any]:
        """Converte a missão para um dicionário para persistência."""
        return {
            "id": self.id,
            "title": self.title,
            "description": self.description,
            "type": self.type,
            "faction": self.faction,
            "reward_credits": self.reward_credits,
            "reputation_impact": self.reputation_impact,
            "objectives": self.objectives,
            "status": self.status.value,
            "target_system": self.target_system,
            "target_entity_id": self.target_entity_id,
            "kill_progress": self.kill_progress,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]):
        """Cria uma missão a partir de um dicionário."""
        mission = cls(
            id=data["id"],
            title=data["title"],
            description=data["description"],
            type=data["type"],
            faction=data["faction"],
            reward_credits=data["reward_credits"],
            reputation_impact=data["reputation_impact"],
            objectives=data["objectives"],
            status=MissionStatus(data["status"]),
            target_system=data.get("target_system", ""),
            target_entity_id=data.get("target_entity_id", ""),
            kill_progress=data.get("kill_progress", 0),
        )
        return mission
