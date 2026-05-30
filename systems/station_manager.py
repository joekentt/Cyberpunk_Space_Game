"""
StationManager — gerencia estações no universo e detecção de docking.

Estados de docking do jogador:
  - "free"          em vôo livre, sem estação por perto
  - "approach"      dentro do docking_radius (pode pressionar F para acoplar)
  - "docked"        atracado, UI de estação aberta (jogo em pausa)
"""
from typing import Dict, List, Optional
from core.event_bus import bus
from entities.station import Station


class StationManager:
    def __init__(self, universe_manager):
        self.universe = universe_manager
        self.stations: Dict[str, Station] = {}
        self._next_id = 0

        # Estado de docking do jogador
        self.docking_state = "free"           # "free" | "approach" | "docked"
        self.current_station_id: Optional[str] = None
        self.last_docked_station_id: Optional[str] = None   # pra respawn

        bus.subscribe("PLAYER_INPUT", self._on_player_input)

    # -- Spawn / inventário ----------------------------------------------

    def spawn_station(self, station: Station) -> str:
        if not station.id:
            station.id = f"station_{self._next_id}"
            self._next_id += 1
        self.stations[station.id] = station
        bus.emit("STATION_SPAWNED", {"id": station.id, "name": station.name})
        return station.id

    def get_station(self, station_id: str) -> Optional[Station]:
        return self.stations.get(station_id)

    def get_all(self) -> List[Station]:
        return list(self.stations.values())

    # -- Update ----------------------------------------------------------

    def update(self, dt: float, player_position=None):
        if self.docking_state == "docked":
            return  # nada a fazer enquanto atracado

        if player_position is None:
            return

        # Encontra a estação mais próxima dentro do raio
        nearest = None
        nearest_dist = float("inf")
        for s in self.stations.values():
            d = s.distance_to(player_position)
            if d < s.docking_radius and d < nearest_dist:
                nearest = s
                nearest_dist = d

        if nearest is None:
            if self.docking_state == "approach":
                bus.emit("DOCKING_EXIT_RANGE", {})
            self.docking_state = "free"
            self.current_station_id = None
        else:
            if self.docking_state != "approach" or self.current_station_id != nearest.id:
                bus.emit("DOCKING_ENTER_RANGE", {
                    "station_id": nearest.id,
                    "station_name": nearest.name,
                })
            self.docking_state = "approach"
            self.current_station_id = nearest.id

    # -- Docking actions -------------------------------------------------

    def request_dock(self) -> bool:
        """Tenta acoplar. Retorna True se conseguiu."""
        if self.docking_state != "approach" or not self.current_station_id:
            return False
        self.docking_state = "docked"
        self.last_docked_station_id = self.current_station_id
        bus.emit("DOCKED", {
            "station_id": self.current_station_id,
            "station": self.stations[self.current_station_id],
        })
        return True

    def undock(self) -> bool:
        """Desacopla, volta ao espaço."""
        if self.docking_state != "docked":
            return False
        station_id = self.current_station_id
        self.docking_state = "approach"  # ainda no raio, mas não atracado
        bus.emit("UNDOCKED", {"station_id": station_id})
        return True

    # -- Listeners -------------------------------------------------------

    def _on_player_input(self, data: dict):
        if data.get("action") == "dock_toggle":
            if self.docking_state == "approach":
                self.request_dock()
            elif self.docking_state == "docked":
                self.undock()

    # -- Respawn ---------------------------------------------------------

    def get_respawn_station(self) -> Optional[Station]:
        """Retorna a última estação onde o jogador acoplou, ou qualquer uma."""
        if self.last_docked_station_id and self.last_docked_station_id in self.stations:
            return self.stations[self.last_docked_station_id]
        if self.stations:
            return next(iter(self.stations.values()))
        return None
