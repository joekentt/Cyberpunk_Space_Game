"""
Projectile — entidade leve para projéteis de combate.
"""
from dataclasses import dataclass, field
from typing import List, Tuple
import math


@dataclass
class Projectile:
    id: str
    owner_id: str                    # id da nave que disparou
    faction: str                     # facção do atirador (para friendly-fire rules)
    position: List[float] = field(default_factory=lambda: [0.0, 0.0])
    velocity: List[float] = field(default_factory=lambda: [0.0, 0.0])

    damage: float = 10.0
    weapon_type: str = "kinetic"     # "kinetic", "laser" (futuro: "missile", "plasma")
    color: Tuple[int, int, int] = (255, 220, 80)  # cor visual (default amarelo)

    lifetime: float = 2.0            # tempo de vida em segundos
    radius: float = 3.0              # raio de colisão

    alive: bool = True               # virou False após hit ou expirar

    def update(self, dt: float):
        if not self.alive:
            return
        self.position[0] += self.velocity[0] * dt
        self.position[1] += self.velocity[1] * dt
        self.lifetime -= dt
        if self.lifetime <= 0:
            self.alive = False

    @staticmethod
    def from_shooter(shooter, weapon_template: dict, projectile_id: str) -> "Projectile":
        """
        Cria um projétil disparado por uma nave usando um template de arma.
        Posição inicial = ponta da frente da nave.
        Velocidade = direção da nave * projectile_speed.
        """
        rad = math.radians(shooter.rotation)
        forward = (math.cos(rad), math.sin(rad))

        # Offset para que o projétil saia da frente da nave (não do centro)
        muzzle_offset = weapon_template.get("muzzle_offset", 25.0)
        pos = [
            shooter.position[0] + forward[0] * muzzle_offset,
            shooter.position[1] + forward[1] * muzzle_offset,
        ]

        speed = weapon_template.get("projectile_speed", 600.0)
        # Soma velocidade da nave para realismo: projétil "carrega" inércia do atirador
        vel = [
            forward[0] * speed + shooter.velocity[0],
            forward[1] * speed + shooter.velocity[1],
        ]

        return Projectile(
            id=projectile_id,
            owner_id=shooter.id,
            faction=getattr(shooter, "faction", "Independent"),
            position=pos,
            velocity=vel,
            damage=weapon_template.get("damage", 10.0),
            weapon_type=weapon_template.get("type", "kinetic"),
            color=weapon_template.get("color", (255, 220, 80)),
            lifetime=weapon_template.get("lifetime", 2.0),
            radius=weapon_template.get("radius", 3.0),
        )
