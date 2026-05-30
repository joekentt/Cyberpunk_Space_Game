from dataclasses import dataclass, field
from typing import Dict, Any

@dataclass
class Module:
    """
    Representa um módulo instalável em uma nave.
    Tudo é data-driven através do dicionário 'stats'.
    """
    id: str
    name: str
    type: str  # Weapon, Engine, Shield, Utility
    stats: Dict[str, Any] = field(default_factory=dict)

    @classmethod
    def from_dict(cls, data: Dict[str, Any]):
        return cls(
            id=data["id"],
            name=data["name"],
            type=data["type"],
            stats=data.get("stats", {})
        )
