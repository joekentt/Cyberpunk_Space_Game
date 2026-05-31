from typing import List, Dict, Any
from entities.ship import Ship
from core.event_bus import bus

class UniverseManager:
    """
    Gerencia todas as entidades (naves, NPCs, projéteis) no universo.
    Responsável pelo spawn, remoção e atualização global.
    """
    def __init__(self):
        self.entities: Dict[str, Ship] = {}
        self.next_id = 1

    def spawn_ship(self, ship_template: Ship, position: List[float]) -> str:
        """Cria uma nova nave no universo, copiando todos os campos do template."""
        entity_id = f"ent_{self.next_id}"
        self.next_id += 1
        
        # Clone completo preservando model_id, hp, shields, faction, etc.
        new_ship = Ship(
            id=entity_id,
            name=ship_template.name,
            ship_class=ship_template.ship_class,
            mass=ship_template.mass,
            energy_capacity=ship_template.energy_capacity,
            heat_dissipation=ship_template.heat_dissipation,
            model_id=ship_template.model_id,
            position=list(position),
            velocity=[0.0, 0.0],
            rotation=0.0,
            current_energy=ship_template.energy_capacity,
            current_heat=0.0,
            current_shields=ship_template.current_shields,
            max_shields=ship_template.max_shields,
            current_hp=ship_template.current_hp,
            max_hp=ship_template.max_hp,
            modules=list(ship_template.modules),
            hardpoints=dict(ship_template.hardpoints),
            is_player=ship_template.is_player,
            faction=ship_template.faction,
            credits=ship_template.credits,
        )
        
        self.entities[entity_id] = new_ship
        bus.emit("ENTITY_SPAWNED", {"id": entity_id, "type": "ship", "pos": position})
        return entity_id

    def remove_entity(self, entity_id: str):
        """Remove uma entidade do universo."""
        if entity_id in self.entities:
            del self.entities[entity_id]
            bus.emit("ENTITY_REMOVED", {"id": entity_id})

    def update(self, dt: float):
        """Atualiza a física de todas as entidades."""
        for entity in self.entities.values():
            entity.apply_physics(dt)
            # Dissipação passiva de calor para todos
            entity.current_heat = max(0.0, entity.current_heat - entity.heat_dissipation * dt)
