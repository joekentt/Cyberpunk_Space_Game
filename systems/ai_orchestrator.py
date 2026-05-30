from core.event_bus import bus
from typing import Dict, List, Any

class AIOrchestrator:
    """
    Orquestra comportamentos de grupo (esquadrões) e táticas de facção em larga escala.
    """
    def __init__(self, universe, npc_mgr):
        self.universe = universe
        self.npc_mgr = npc_mgr
        self.squads = {} # faction -> list of npc_ids
        
        bus.subscribe("ENTITY_SPAWNED", self.on_ship_spawned)
        bus.subscribe("SHIP_DESTROYED", self.on_ship_destroyed)
        bus.subscribe("ENTITY_REMOVED", self.on_ship_destroyed)
        bus.subscribe("TICK", self.update)

    def on_ship_spawned(self, data: Dict[str, Any]):
        ship_id = data["id"]
        ship = self.universe.entities.get(ship_id)
        if ship and not ship.is_player:
            faction = getattr(ship, 'faction', 'Independent')
            if faction not in self.squads:
                self.squads[faction] = []
            self.squads[faction].append(ship_id)

    def on_ship_destroyed(self, data: Dict[str, Any]):
        ship_id = data.get("ship_id") or data.get("id")
        for faction in self.squads:
            if ship_id in self.squads[faction]:
                self.squads[faction].remove(ship_id)
                # Se um membro da facção é destruído, outros podem entrar em modo vingança
                self._trigger_faction_retaliation(faction, data.get("attacker_id"))
                break

    def _trigger_faction_retaliation(self, faction: str, attacker_id: Any):
        """Faz com que membros próximos da mesma facção ataquem o agressor."""
        if not attacker_id: return
        
        for npc_id in self.squads.get(faction, []):
            # Apenas NPCs próximos ou em alerta
            self.npc_mgr.register_npc(npc_id, initial_state="CHASE")
            # Aqui poderíamos emitir um diálogo de rádio
            bus.emit("DIALOGUE_TRIGGERED", {
                "speaker": f"Unit_{npc_id}",
                "text": "Membro da esquadra abatido! Engajando agressor!",
                "category": "COMBAT_START"
            })

    def update(self, dt: float):
        """
        Analisa o estado global para tomar decisões táticas.
        Ex: Se uma facção está perdendo muitos membros, ordena retirada geral.
        """
        for faction, members in self.squads.items():
            if len(members) > 0:
                # Lógica tática simplificada
                pass
