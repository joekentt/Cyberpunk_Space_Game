"""
CombatManager — orquestra todo o ciclo de combate:
  - Disparos (cria projéteis)
  - Movimento de projéteis (a cada update)
  - Detecção de colisão (projétil × nave)
  - Aplicação de dano (escudos → casco)
  - Destruição de naves (HULL <= 0)

Eventos emitidos via EventBus:
  - WEAPON_FIRED      {shooter_id, weapon_type, position, color}
  - PROJECTILE_HIT    {target_id, position, damage, color}
  - SHIP_DESTROYED    {ship_id, position, faction}
"""
import math
from typing import Dict, List
from core.event_bus import bus
from entities.projectile import Projectile


# Templates de arma padrão. No futuro virão dos Modules equipados.
DEFAULT_WEAPONS = {
    "kinetic_small": {
        "type": "kinetic",
        "damage": 8.0,
        "projectile_speed": 700.0,
        "lifetime": 1.5,
        "radius": 3.0,
        "muzzle_offset": 22.0,
        "color": (255, 200, 80),
        "cooldown": 0.25,        # tiros por segundo = 1/cooldown = 4
    },
    "kinetic_medium": {
        "type": "kinetic",
        "damage": 18.0,
        "projectile_speed": 600.0,
        "lifetime": 2.0,
        "radius": 4.0,
        "muzzle_offset": 28.0,
        "color": (255, 160, 60),
        "cooldown": 0.5,
    },
    "laser_small": {
        "type": "laser",
        "damage": 4.0,
        "projectile_speed": 1200.0,
        "lifetime": 0.6,
        "radius": 2.5,
        "muzzle_offset": 22.0,
        "color": (80, 220, 255),
        "cooldown": 0.10,
    },
}


class CombatManager:
    def __init__(self, universe_manager):
        self.universe = universe_manager
        self.projectiles: Dict[str, Projectile] = {}
        self._next_id = 0

        # Cooldowns por (ship_id, weapon_slot)
        self.cooldowns: Dict[str, float] = {}

        # Tabela de hostilidade entre facções (poderia vir do FactionManager)
        # Por padrão, todas as facções podem atacar todas (PvE)
        self.hostility_table = {
            ("Pirates", "United Humans"): True,
            ("Pirates", "Independent"): True,
            ("Pirates", "Marth"): True,
            ("United Humans", "Pirates"): True,
            ("Orcs", "United Humans"): True,
            ("Marth", "Pirates"): True,
        }

        bus.subscribe("PLAYER_INPUT", self._on_player_input)
        bus.subscribe("NPC_FIRE", self._on_npc_fire)

    # ----- API pública --------------------------------------------------

    def fire(self, shooter, weapon_id: str = "kinetic_small") -> bool:
        """Tenta disparar uma arma. Retorna True se conseguiu (cooldown OK)."""
        cd_key = f"{shooter.id}:{weapon_id}"
        if self.cooldowns.get(cd_key, 0.0) > 0.0:
            return False

        template = DEFAULT_WEAPONS.get(weapon_id, DEFAULT_WEAPONS["kinetic_small"])

        proj = Projectile.from_shooter(
            shooter=shooter,
            weapon_template=template,
            projectile_id=f"proj_{self._next_id}",
        )
        self._next_id += 1
        self.projectiles[proj.id] = proj
        self.cooldowns[cd_key] = template["cooldown"]

        bus.emit("WEAPON_FIRED", {
            "shooter_id": shooter.id,
            "weapon_type": template["type"],
            "position": list(proj.position),
            "color": template["color"],
            "rotation": shooter.rotation,
        })
        return True

    # ----- Bus listeners ------------------------------------------------

    def _on_player_input(self, data: dict):
        if data.get("action") != "shoot":
            return
        # Procura a ship do player no universo
        player_ship = self._find_player_ship()
        if player_ship is None:
            return
        self.fire(player_ship, weapon_id="kinetic_small")

    def _on_npc_fire(self, data: dict):
        """Disparado pelo NPCManager quando uma IA decide atirar."""
        shooter_id = data.get("shooter_id")
        weapon_id = data.get("weapon_id", "kinetic_small")
        shooter = self.universe.entities.get(shooter_id)
        if shooter is None:
            return
        self.fire(shooter, weapon_id=weapon_id)

    # ----- Update por frame ---------------------------------------------

    def update(self, dt: float):
        # 1. Tick de cooldowns
        for k in list(self.cooldowns.keys()):
            self.cooldowns[k] = max(0.0, self.cooldowns[k] - dt)

        # 2. Move projéteis e detecta colisão
        to_remove = []
        for pid, proj in self.projectiles.items():
            proj.update(dt)
            if not proj.alive:
                to_remove.append(pid)
                continue
            hit = self._check_hit(proj)
            if hit is not None:
                self._apply_hit(proj, hit)
                to_remove.append(pid)

        # 3. Limpa projéteis mortos
        for pid in to_remove:
            del self.projectiles[pid]

    # ----- Internals ----------------------------------------------------

    def _find_player_ship(self):
        for e in self.universe.entities.values():
            if getattr(e, "is_player", False):
                return e
        return None

    def _check_hit(self, proj: Projectile):
        """Verifica colisão com naves (esfera vs esfera). Retorna a Ship atingida ou None."""
        for ship_id, ship in self.universe.entities.items():
            if ship_id == proj.owner_id:
                continue
            # Mesma facção do atirador NÃO toma dano (friendly-fire desligado)
            if getattr(ship, "faction", None) == proj.faction:
                continue
            # Distância
            dx = ship.position[0] - proj.position[0]
            dy = ship.position[1] - proj.position[1]
            dist_sq = dx * dx + dy * dy
            ship_radius = self._ship_collision_radius(ship)
            r = proj.radius + ship_radius
            if dist_sq <= r * r:
                return ship
        return None

    @staticmethod
    def _ship_collision_radius(ship) -> float:
        """Raio aproximado de colisão por classe."""
        return {
            "Small": 18.0,
            "Medium": 28.0,
            "Large": 40.0,
        }.get(getattr(ship, "ship_class", "Small"), 20.0)

    def _apply_hit(self, proj: Projectile, target):
        """Aplica dano: escudos absorvem primeiro, depois casco."""
        damage = proj.damage

        # Escudos
        current_shields = getattr(target, "current_shields", 0.0)
        if current_shields > 0:
            absorbed = min(damage, current_shields)
            target.current_shields = current_shields - absorbed
            damage -= absorbed

        # Casco (transborda)
        if damage > 0:
            current_hp = getattr(target, "current_hp", 100.0)
            target.current_hp = max(0.0, current_hp - damage)

        # Evento de hit (VFX vai escutar)
        bus.emit("PROJECTILE_HIT", {
            "target_id": target.id,
            "position": list(proj.position),
            "damage": proj.damage,
            "color": proj.color,
            "shield_hit": current_shields > 0,
        })

        # Verifica destruição — propaga o atirador para o evento
        if getattr(target, "current_hp", 1.0) <= 0.0:
            self._destroy_ship(target, attacker_id=proj.owner_id)

    def _destroy_ship(self, ship, attacker_id: str = None):
        """Marca a nave como destruída e emite eventos."""
        bus.emit("SHIP_DESTROYED", {
            "ship_id": ship.id,
            "position": list(ship.position),
            "faction": getattr(ship, "faction", "Independent"),
            "ship_class": getattr(ship, "ship_class", "Small"),
            "attacker_id": attacker_id,   # quem disparou o tiro fatal
        })
        # Remove do universo
        if ship.id in self.universe.entities:
            del self.universe.entities[ship.id]
            bus.emit("ENTITY_REMOVED", {"id": ship.id})
