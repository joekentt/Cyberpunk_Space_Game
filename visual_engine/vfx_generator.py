"""
VFXGenerator — efeitos visuais dinâmicos.

Inclui:
  - Rastro de motor (engine_trail)
  - Muzzle flash (clarão de disparo)
  - Impact (faíscas de impacto em alvo)
  - Shield hit (anel hexagonal de escudo)
  - Explosion (explosão de nave destruída)
  - Render de projéteis (visual baseado em weapon_type)

Tudo se inscreve no EventBus para reagir a eventos de combate.
"""
import math
import random
from typing import List, Tuple, Optional
import pygame
from core.event_bus import bus


# ---------------------------------------------------------------- Particle

class Particle:
    """Partícula simples com posição, velocidade, cor e vida."""
    def __init__(self, pos, vel, color, life: float, size: int = 2, fade: bool = True):
        self.pos = list(pos)
        self.vel = list(vel)
        self.color = color
        self.life = life
        self.max_life = life
        self.size = size
        self.fade = fade

    def update(self, dt: float):
        self.pos[0] += self.vel[0] * dt
        self.pos[1] += self.vel[1] * dt
        self.vel[0] *= 0.92 ** (dt * 60)
        self.vel[1] *= 0.92 ** (dt * 60)
        self.life -= dt

    def draw(self, screen: pygame.Surface, camera_offset):
        if self.life <= 0:
            return
        alpha = int((self.life / self.max_life) * 255) if self.fade else 255
        alpha = max(0, min(255, alpha))
        s = pygame.Surface((self.size, self.size), pygame.SRCALPHA)
        s.fill((*self.color, alpha))
        screen.blit(s, (
            int(self.pos[0] - camera_offset[0] - self.size // 2),
            int(self.pos[1] - camera_offset[1] - self.size // 2)
        ))


# ---------------------------------------------------------------- ShieldRing

class ShieldRing:
    """Anel hexagonal de escudo que pisca brevemente quando atingido."""
    def __init__(self, target_ship, color, life: float = 0.4):
        self.target = target_ship
        self.color = color
        self.life = life
        self.max_life = life
        self.size = 40

    def update(self, dt: float):
        self.life -= dt

    def draw(self, screen, camera_offset):
        if self.life <= 0 or self.target is None:
            return
        alpha = int((self.life / self.max_life) * 180)
        radius = self.size + int((1 - self.life / self.max_life) * 12)
        cx = int(self.target.position[0] - camera_offset[0])
        cy = int(self.target.position[1] - camera_offset[1])
        pts = []
        for i in range(6):
            ang = math.radians(60 * i)
            pts.append((cx + math.cos(ang) * radius, cy + math.sin(ang) * radius))
        surf = pygame.Surface(screen.get_size(), pygame.SRCALPHA)
        pygame.draw.polygon(surf, (*self.color[:3], alpha), pts, width=2)
        screen.blit(surf, (0, 0))


# ---------------------------------------------------------------- Render projétil

def render_projectile(screen: pygame.Surface, proj_pos, proj_color, weapon_type,
                      camera_offset, rotation: float = 0.0):
    """Desenha um projétil com glow apropriado ao tipo de arma."""
    cx = int(proj_pos[0] - camera_offset[0])
    cy = int(proj_pos[1] - camera_offset[1])

    if weapon_type == "laser":
        rad = math.radians(rotation)
        length = 14
        x2 = cx + math.cos(rad) * length
        y2 = cy + math.sin(rad) * length
        for w, a in [(5, 70), (3, 140), (1, 255)]:
            surf = pygame.Surface(screen.get_size(), pygame.SRCALPHA)
            pygame.draw.line(surf, (*proj_color[:3], a),
                             (cx, cy), (x2, y2), width=w)
            screen.blit(surf, (0, 0))
    else:
        # Kinetic: pequena bala com glow
        for r, a in [(6, 50), (4, 110), (2, 200)]:
            surf = pygame.Surface((r * 2 + 1, r * 2 + 1), pygame.SRCALPHA)
            pygame.draw.circle(surf, (*proj_color[:3], a), (r, r), r)
            screen.blit(surf, (cx - r, cy - r))
        pygame.draw.circle(screen, proj_color, (cx, cy), 1)


# ---------------------------------------------------------------- VFXGenerator

class VFXGenerator:
    def __init__(self):
        self.particles: List[Particle] = []
        self.shield_rings: List[ShieldRing] = []
        self.universe = None

        bus.subscribe("WEAPON_FIRED", self._on_weapon_fired)
        bus.subscribe("PROJECTILE_HIT", self._on_projectile_hit)
        bus.subscribe("SHIP_DESTROYED", self._on_ship_destroyed)

    def set_universe(self, universe_manager):
        self.universe = universe_manager

    def create_thruster_jet(self, origin, jet_dir_deg: float, color, *,
                            count: int = 2, speed_range=(80, 140), size: int = 2,
                            life_range=(0.25, 0.45), spread: float = 20.0):
        """
        Emite um jato de partículas a partir de `origin`, viajando na direção
        `jet_dir_deg` (graus, sentido do escape do gás). É a base comum para o
        motor principal (rastro grande) e os thrusters de RCS (jatos curtos).

        A hierarquia de força é expressa pelos parâmetros: mais `count`, `size`,
        `speed_range` e `life_range` = jato maior/mais forte.
        """
        rad = math.radians(jet_dir_deg)
        for _ in range(count):
            speed = random.uniform(*speed_range)
            vel = [math.cos(rad) * speed + random.uniform(-spread, spread),
                   math.sin(rad) * speed + random.uniform(-spread, spread)]
            self.particles.append(Particle(
                origin, vel, color, life=random.uniform(*life_range),
                size=size, fade=True
            ))

    def create_engine_trail(self, pos, angle: float, color):
        """Motor principal: rastro grande, escape na direção OPOSTA ao bico."""
        self.create_thruster_jet(
            pos, angle + 180, color,
            count=2, speed_range=(80, 140), size=2,
            life_range=(0.25, 0.45), spread=20.0,
        )

    def create_rcs_puff(self, origin, jet_dir_deg: float, color,
                        strength: str = "reverse"):
        """
        Thruster de manobra (RCS): jato curto e rápido, mais sutil que o motor.

        strength="reverse" → RCS de freio/ré (médio, mais fraco que o motor).
        strength="strafe"  → RCS lateral (o mais fraco de todos).
        """
        if strength == "strafe":
            # O mais fraco: jato curtíssimo, pouca partícula, pequeno.
            self.create_thruster_jet(
                origin, jet_dir_deg, color,
                count=1, speed_range=(40, 75), size=1,
                life_range=(0.10, 0.18), spread=10.0,
            )
        else:  # "reverse" — médio
            self.create_thruster_jet(
                origin, jet_dir_deg, color,
                count=2, speed_range=(55, 95), size=2,
                life_range=(0.15, 0.28), spread=14.0,
            )

    def _on_weapon_fired(self, data):
        pos = data.get("position", (0, 0))
        color = data.get("color", (255, 200, 80))
        rotation = data.get("rotation", 0.0)
        rad = math.radians(rotation)
        for _ in range(4):
            spread = random.uniform(-0.3, 0.3)
            speed = random.uniform(120, 220)
            ang = rad + spread
            vel = [math.cos(ang) * speed, math.sin(ang) * speed]
            self.particles.append(Particle(
                pos, vel, color, life=0.12, size=3, fade=True
            ))
        self.particles.append(Particle(
            pos, [0, 0], (255, 255, 220),
            life=0.06, size=5, fade=True
        ))

    def _on_projectile_hit(self, data):
        pos = data.get("position", (0, 0))
        color = data.get("color", (255, 200, 80))
        shield_hit = data.get("shield_hit", False)
        target_id = data.get("target_id")

        n = 8 if not shield_hit else 5
        for _ in range(n):
            ang = random.uniform(0, math.tau)
            speed = random.uniform(60, 180)
            vel = [math.cos(ang) * speed, math.sin(ang) * speed]
            spark_color = (255, 240, 200) if not shield_hit else color
            self.particles.append(Particle(
                pos, vel, spark_color,
                life=random.uniform(0.2, 0.4), size=2, fade=True
            ))

        if shield_hit and target_id and self.universe:
            target = self.universe.entities.get(target_id)
            if target:
                self.shield_rings.append(ShieldRing(target, (80, 180, 255)))

    def _on_ship_destroyed(self, data):
        pos = data.get("position", (0, 0))
        ship_class = data.get("ship_class", "Small")
        n_particles = {"Small": 30, "Medium": 50, "Large": 80}.get(ship_class, 30)
        max_speed = {"Small": 300, "Medium": 400, "Large": 500}.get(ship_class, 300)

        for _ in range(n_particles):
            ang = random.uniform(0, math.tau)
            speed = random.uniform(80, max_speed)
            vel = [math.cos(ang) * speed, math.sin(ang) * speed]
            colors = [(255, 240, 180), (255, 180, 80), (255, 90, 30), (200, 50, 20)]
            self.particles.append(Particle(
                pos, vel, random.choice(colors),
                life=random.uniform(0.5, 1.2),
                size=random.choice([3, 4, 4, 5]),
                fade=True
            ))
        self.particles.append(Particle(
            pos, [0, 0], (255, 255, 240), life=0.15, size=12, fade=True
        ))

    def update(self, dt: float):
        for p in self.particles:
            p.update(dt)
        self.particles = [p for p in self.particles if p.life > 0]
        for s in self.shield_rings:
            s.update(dt)
        self.shield_rings = [s for s in self.shield_rings if s.life > 0]

    def draw(self, screen, camera_offset):
        for p in self.particles:
            p.draw(screen, camera_offset)
        for s in self.shield_rings:
            s.draw(screen, camera_offset)
