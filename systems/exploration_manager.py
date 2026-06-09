"""
ExplorationManager — POIs do setor, fog-of-war e descoberta (ver ADR 011).

Dono do conjunto de `PointOfInterest` do setor. Três canais de descoberta:
  1. Proximidade: `update(dt, player_pos)` marca POIs dentro de
     `balance.exploration["discover_radius"]` e emite `POI_DISCOVERED`
     (uma única vez por POI).
  2. Drop de dados de localização: `reveal_random_hidden()` (chamado pelo
     main ao processar loot com "location_data").
  3. Cartografia: escuta `CARTOGRAPHY_PURCHASED` no bus (emitido pela
     StationUI após debitar créditos) e revela N POIs ocultos.

`POI_DISCOVERED` carrega `source` ("proximity" / "location_data" /
"cartography") para o feedback visual diferenciar.

Segue a regra do mundo (ADR 005): criado em `_build_world_systems` (após o
clear do bus), zerado em `_teardown_world`. Persistência aditiva: o save
guarda só os IDs descobertos (`get_save_data`/`load_save_data`); IDs
desconhecidos são ignorados no load.

Módulo puro (sem pygame) — testável headless.
"""
import math
import random as _random
from typing import Any, Dict, List, Optional

from core.event_bus import bus
from core.balance import balance
from entities.poi import PointOfInterest


class ExplorationManager:
    def __init__(self, rng=None):
        self.pois: Dict[str, PointOfInterest] = {}
        self.discover_radius: float = balance.exploration["discover_radius"]
        self._rng = rng or _random
        bus.subscribe("CARTOGRAPHY_PURCHASED", self._on_cartography)

    # ------------------------------------------------------------------ setup
    def register_poi(self, poi: PointOfInterest):
        self.pois[poi.id] = poi

    def register_station(self, station):
        """
        Estações entram como POIs automaticamente, JÁ descobertas (as 3
        iniciais são conhecidas do piloto — ver ADR 011).
        """
        self.register_poi(PointOfInterest(
            id=f"poi_{station.id}",
            name=station.name,
            kind="station",
            position=list(station.position),
            discovered=True,
        ))

    # ------------------------------------------------------------------ consultas
    def get_all(self) -> List[PointOfInterest]:
        return list(self.pois.values())

    def discovered(self) -> List[PointOfInterest]:
        return [p for p in self.pois.values() if p.discovered]

    def hidden(self) -> List[PointOfInterest]:
        return [p for p in self.pois.values() if not p.discovered]

    def hidden_count(self) -> int:
        return len(self.hidden())

    # ------------------------------------------------------------------ descoberta
    def update(self, dt: float, player_pos):
        """Descoberta por proximidade. Emite POI_DISCOVERED uma vez por POI."""
        for poi in self.pois.values():
            if poi.discovered:
                continue
            dx = poi.position[0] - player_pos[0]
            dy = poi.position[1] - player_pos[1]
            if math.hypot(dx, dy) <= self.discover_radius:
                self._discover(poi, "proximity")

    def reveal_random_hidden(self, source: str = "location_data"
                             ) -> Optional[PointOfInterest]:
        """
        Revela UM POI oculto aleatório (drop de dados de localização).
        Sem POI oculto → None, sem crash (no-op).
        """
        hidden = self.hidden()
        if not hidden:
            return None
        poi = self._rng.choice(hidden)
        self._discover(poi, source)
        return poi

    def reveal_hidden(self, count: int, source: str = "cartography"
                      ) -> List[PointOfInterest]:
        """Revela até `count` POIs ocultos aleatórios (cartografia)."""
        revealed = []
        for _ in range(max(0, int(count))):
            poi = self.reveal_random_hidden(source)
            if poi is None:
                break
            revealed.append(poi)
        return revealed

    def _discover(self, poi: PointOfInterest, source: str):
        poi.discovered = True
        bus.emit("POI_DISCOVERED", {
            "poi_id": poi.id,
            "name": poi.name,
            "kind": poi.kind,
            "position": list(poi.position),
            "source": source,
        })

    # ------------------------------------------------------------------ bus
    def _on_cartography(self, data):
        count = int((data or {}).get(
            "count", balance.exploration["cartography_reveal_count"]))
        self.reveal_hidden(count, source="cartography")

    # ------------------------------------------------------------------ save/load
    def get_save_data(self) -> Dict[str, Any]:
        return {"discovered_ids": [p.id for p in self.pois.values() if p.discovered]}

    def load_save_data(self, data: Dict[str, Any]):
        """Aplica os IDs descobertos do save. IDs desconhecidos são ignorados."""
        for pid in (data or {}).get("discovered_ids", []):
            poi = self.pois.get(pid)
            if poi is not None:
                poi.discovered = True
