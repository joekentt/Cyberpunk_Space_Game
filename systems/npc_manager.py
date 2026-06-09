import math
import random
from typing import Dict, List, Any, Optional
from core.event_bus import bus
from core.balance import balance
from entities.ship import Ship
from systems import factions_util

class NPCBehavior:
    IDLE = "IDLE"
    CHASE = "CHASE"
    ATTACK = "ATTACK"
    FLEE = "FLEE"
    ESCORT = "ESCORT"

class NPCManager:
    """
    Gerencia a IA de todos os NPCs e o sistema de Wingmen (Pilotos Recrutados).
    """
    def __init__(self, universe_manager):
        self.universe = universe_manager
        self.npc_ships: Dict[str, str] = {} # ship_id: behavior_state
        self.wingmen: List[str] = [] # Lista de ship_ids que são wingmen do jogador
        self.targets: Dict[str, str] = {} # ship_id: target_ship_id
        
        # Parâmetros de IA (números de combate vêm de data/balance.json)
        self.thrust_power = 400.0
        self.rotation_speed = 120.0
        self.attack_range = balance.ai["attack_range"]
        self.detection_range = balance.ai["detection_range"]
        self.fire_chance_per_tick = balance.ai["fire_chance_per_tick"]
        self.flee_shield_threshold = balance.ai["flee_shield_threshold"]
        self.recover_shield_threshold = balance.ai["recover_shield_threshold"]

        # Inscrição em eventos
        bus.subscribe("TICK", self.update)
        bus.subscribe("ENTITY_REMOVED", self.on_entity_removed)
        bus.subscribe("RECRUIT_WINGMAN", self.recruit_wingman)

    def register_npc(self, ship_id: str, initial_state: str = NPCBehavior.IDLE):
        self.npc_ships[ship_id] = initial_state

    def recruit_wingman(self, ship_id: str):
        """Recruta uma nave NPC para ser wingman do jogador."""
        if len(self.wingmen) < 2:
            if ship_id in self.npc_ships:
                self.wingmen.append(ship_id)
                self.npc_ships[ship_id] = NPCBehavior.ESCORT
                bus.emit("WINGMAN_RECRUITED", {"ship_id": ship_id})

    def on_entity_removed(self, data: Dict[str, Any]):
        ship_id = data.get("id")
        if ship_id in self.npc_ships:
            del self.npc_ships[ship_id]
        if ship_id in self.wingmen:
            self.wingmen.remove(ship_id)
        if ship_id in self.targets:
            del self.targets[ship_id]

    def update(self, dt: float):
        player_ship = self._get_player_ship()
        
        for ship_id, state in list(self.npc_ships.items()):
            ship = self.universe.entities.get(ship_id)
            if not ship: continue

            if state == NPCBehavior.ESCORT:
                self._handle_escort(ship, player_ship, dt)
            elif state == NPCBehavior.CHASE:
                target_id = self.targets.get(ship_id)
                target = self.universe.entities.get(target_id) if target_id else player_ship
                self._handle_chase(ship, target, dt)
            elif state == NPCBehavior.FLEE:
                self._handle_flee(ship, player_ship, dt)
            elif state == NPCBehavior.ATTACK:
                target_id = self.targets.get(ship_id)
                target = self.universe.entities.get(target_id) if target_id else player_ship
                self._handle_attack(ship, target, dt)
            else:
                # IDLE: detecta jogador hostil próximo e entra em CHASE
                ship.rotation += 10.0 * dt
                if player_ship and self._is_hostile(ship, player_ship):
                    dist = self._get_distance(ship.position, player_ship.position)
                    if dist < self.detection_range:
                        self.targets[ship_id] = player_ship.id
                        self.npc_ships[ship_id] = NPCBehavior.CHASE

    def _handle_escort(self, ship: Ship, leader: Optional[Ship], dt: float):
        if not leader: return
        
        # Posição de formação (atrás e ao lado)
        offset_x = -60 if self.wingmen.index(ship.id) == 0 else 60
        target_pos = [leader.position[0] + offset_x, leader.position[1] + 60]
        
        dist = self._get_distance(ship.position, target_pos)
        if dist > 50:
            angle = math.degrees(math.atan2(target_pos[1] - ship.position[1], target_pos[0] - ship.position[0]))
            self._rotate_towards(ship, angle, dt)
            self._accelerate(ship, dt)
        else:
            # Combina velocidade e rotação
            ship.velocity = [leader.velocity[0], leader.velocity[1]]
            self._rotate_towards(ship, leader.rotation, dt)

    def _handle_chase(self, ship: Ship, target: Optional[Ship], dt: float):
        if not target: return
        dist = self._get_distance(ship.position, target.position)
        angle = math.degrees(math.atan2(target.position[1] - ship.position[1], target.position[0] - ship.position[0]))
        
        self._rotate_towards(ship, angle, dt)
        self._accelerate(ship, dt)
        
        if dist < self.attack_range:
            self.npc_ships[ship.id] = NPCBehavior.ATTACK

    def _handle_attack(self, ship: Ship, target: Optional[Ship], dt: float):
        if not target: 
            self.npc_ships[ship.id] = NPCBehavior.IDLE
            return
            
        dist = self._get_distance(ship.position, target.position)
        angle = math.degrees(math.atan2(target.position[1] - ship.position[1], target.position[0] - ship.position[0]))
        
        self._rotate_towards(ship, angle, dt)
        if dist > self.attack_range * 0.6:
            self._accelerate(ship, dt)
            
        if random.random() < self.fire_chance_per_tick: # cooldown checado pelo CombatManager
            bus.emit("NPC_FIRE", {
                "shooter_id": ship.id,
                "weapon_id": "kinetic_small",
                "target_id": target.id,
            })

        if ship.current_shields < self.flee_shield_threshold:
            self.npc_ships[ship.id] = NPCBehavior.FLEE

    def _handle_flee(self, ship: Ship, threat: Optional[Ship], dt: float):
        if not threat: return
        angle = math.degrees(math.atan2(threat.position[1] - ship.position[1], threat.position[0] - ship.position[0]))
        self._rotate_towards(ship, angle + 180, dt)
        self._accelerate(ship, dt)

        if ship.current_shields > self.recover_shield_threshold:
            self.npc_ships[ship.id] = NPCBehavior.CHASE

    def _rotate_towards(self, ship: Ship, target_angle: float, dt: float):
        angle_diff = (target_angle - ship.rotation + 180) % 360 - 180
        if abs(angle_diff) > 1.0:
            direction = 1.0 if angle_diff > 0 else -1.0
            ship.rotation += direction * self.rotation_speed * dt

    def _accelerate(self, ship: Ship, dt: float):
        forward = ship.get_forward_vector()
        accel = (self.thrust_power / ship.mass)
        ship.velocity[0] += forward[0] * accel * dt
        ship.velocity[1] += forward[1] * accel * dt
        ship.current_heat += 1.5 * dt

    def _get_distance(self, pos1: List[float], pos2: List[float]) -> float:
        return math.sqrt((pos1[0]-pos2[0])**2 + (pos1[1]-pos2[1])**2)

    def _get_player_ship(self) -> Optional[Ship]:
        for entity in self.universe.entities.values():
            if getattr(entity, 'is_player', False):
                return entity
        return None

    # Hostilidade vem da fonte única `systems/factions_util` (ver ADR 008).
    # Alias de classe mantido por compatibilidade (testes/legado).
    HOSTILITY = factions_util.HOSTILITY

    def _is_hostile(self, attacker: Ship, target: Ship) -> bool:
        fa = getattr(attacker, "faction", "Independent")
        ft = getattr(target, "faction", "Independent")
        return factions_util.is_hostile(fa, ft)
