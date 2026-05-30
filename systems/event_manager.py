import random
from typing import Dict, Any, List
from core.event_bus import bus

class EventManager:
    """
    Orquestra eventos dinâmicos no universo (ataques piratas, crises, etc.).
    """
    def __init__(self, universe_manager, faction_manager):
        self.universe = universe_manager
        self.faction_mgr = faction_manager
        self.active_events: List[Dict[str, Any]] = []
        
        # Inscrição em eventos
        bus.subscribe("TICK", self.update)

    def update(self, dt: float):
        """Verifica gatilhos para novos eventos dinâmicos."""
        # Chance aleatória de disparar um evento a cada tick (muito baixa)
        if random.random() < (0.001 * dt):
            self.trigger_random_event()

    def trigger_random_event(self):
        event_types = ["PIRATE_RAID", "ECONOMIC_BOOM", "FACTION_CONFLICT"]
        event_type = random.choice(event_types)
        
        if event_type == "PIRATE_RAID":
            self._spawn_pirate_raid()
        elif event_type == "ECONOMIC_BOOM":
            self._trigger_economic_boom()
        elif event_type == "FACTION_CONFLICT":
            self._trigger_faction_conflict()

    def _spawn_pirate_raid(self):
        """Gera um ataque pirata no sistema atual."""
        bus.emit("DYNAMIC_EVENT_STARTED", {
            "type": "PIRATE_RAID",
            "description": "Sinais de naves piratas detectados no setor!"
        })
        # No MVP, apenas emitimos o evento. 
        # Em um sistema completo, o UniverseManager spawnaria naves aqui.

    def _trigger_economic_boom(self):
        """Melhora temporariamente os preços em uma facção."""
        faction = random.choice(list(self.faction_mgr.factions.keys()))
        bus.emit("DYNAMIC_EVENT_STARTED", {
            "type": "ECONOMIC_BOOM",
            "faction": faction,
            "description": f"Boom econômico em {faction}! Preços de mercado melhorados."
        })
        # Impacto temporário no Economic Value
        bus.emit("UPDATE_REPUTATION", {
            "faction": faction,
            "impact": {"economic_value": 10}
        })

    def _trigger_faction_conflict(self):
        """Gera tensão entre duas facções."""
        factions = list(self.faction_mgr.factions.keys())
        if len(factions) >= 2:
            f1, f2 = random.sample(factions, 2)
            bus.emit("DYNAMIC_EVENT_STARTED", {
                "type": "FACTION_CONFLICT",
                "factions": [f1, f2],
                "description": f"Tensões diplomáticas entre {f1} e {f2} aumentaram."
            })
