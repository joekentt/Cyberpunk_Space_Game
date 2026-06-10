"""
PointOfInterest — entidade de DADOS pura para exploração (ver ADR 011).

POIs NÃO entram em `universe.entities` (não poluem o universo de combate com
objetos não-naves). O dono do conjunto é o `ExplorationManager`. Neste ciclo
os POIs são visuais/navegacionais: aparecem no mapa estelar e no radar quando
descobertos, sem presença física no mundo.
"""
from dataclasses import dataclass, field
from typing import Any, Dict, List

# Tipos válidos de POI (kind)
POI_KINDS = ("station", "asteroid_field", "signal", "derelict")


@dataclass
class PointOfInterest:
    id: str
    name: str
    kind: str                                   # um de POI_KINDS
    position: List[float] = field(default_factory=lambda: [0.0, 0.0])
    discovered: bool = False
    data: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "name": self.name,
            "kind": self.kind,
            "position": list(self.position),
            "discovered": self.discovered,
            "data": dict(self.data),
        }

    @classmethod
    def from_dict(cls, d: Dict[str, Any]) -> "PointOfInterest":
        return cls(
            id=d["id"],
            name=d.get("name", d["id"]),
            kind=d.get("kind", "signal"),
            position=list(d.get("position", [0.0, 0.0])),
            discovered=bool(d.get("discovered", False)),
            data=dict(d.get("data", {})),
        )
