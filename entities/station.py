"""
Station — entidade estacionária no espaço.
Oferece serviços (mercado de naves, reparo, missões — alguns ainda placeholder)
e atua como ponto de respawn.
"""
from dataclasses import dataclass, field
from typing import List, Dict, Any


@dataclass
class Station:
    id: str
    name: str
    position: List[float] = field(default_factory=lambda: [0.0, 0.0])
    faction: str = "Independent"

    # Visual
    station_class: str = "Hub"           # "Hub", "Outpost", "Refinery" (futuro)
    model_id: str = None                  # perfil em STATION_PROFILES

    # Gameplay
    docking_radius: float = 180.0         # quando player está dentro, pode acoplar
    dock_pull_radius: float = 50.0        # confirmação de docking
    services: List[str] = field(default_factory=lambda: ["shipyard", "repair", "refuel"])

    # Inventário de naves à venda (lista de model_ids do ships.json)
    ship_inventory: List[str] = field(default_factory=list)

    # Estado dinâmico do sprite (não-rotacionável: rotation fixa em zero)
    rotation: float = 0.0
    spin: float = 0.0                     # rotação visual do anel central (estética)

    def distance_to(self, position) -> float:
        import math
        dx = self.position[0] - position[0]
        dy = self.position[1] - position[1]
        return math.sqrt(dx * dx + dy * dy)
