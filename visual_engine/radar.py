"""
Radar / scanner de proximidade (ver ADR 008).

Overlay de HUD circular, estilo Elite, fixo no canto. Lê posições já
existentes (`universe.entities`, `station_mgr.get_all()`) relativas ao player
e desenha blips coloridos por relação de facção. **Puramente de apresentação**:
não toca lógica de jogo.

A matemática de projeção fica em `radar_math.py` (pura, testável headless);
esta classe só desenha. As cores de relação reutilizam o mesmo vocabulário
visual do HUD de combate (vermelho hostil, etc.).

Importante: o alcance do radar é uma ajuda de UX e **não** é o alcance de
detecção da IA. Ver um blip não significa que aquela nave já te detectou.
"""
import pygame
from typing import Iterable

from visual_engine.radar_math import radar_project
from systems.factions_util import relation

# Cores por relação (alinhadas ao HUD de combate).
COLOR_HOSTILE = (235, 45, 45)
COLOR_NEUTRAL = (210, 200, 90)
COLOR_ALLY    = (60, 200, 255)
COLOR_STATION = (60, 220, 120)
COLOR_PLAYER  = (255, 255, 255)
COLOR_POI     = (180, 130, 255)   # POIs descobertos (ADR 011)

_RELATION_COLOR = {
    "hostile": COLOR_HOSTILE,
    "neutral": COLOR_NEUTRAL,
    "ally":    COLOR_ALLY,
}


class Radar:
    def __init__(self, screen_w: int, screen_h: int, world_range: float = 2000.0,
                 disc_radius: int = 80, margin: int = 18):
        self.screen_w = screen_w
        self.screen_h = screen_h
        self.world_range = float(world_range)
        self.disc_radius = int(disc_radius)
        # Centro do disco: canto inferior direito.
        self.cx = screen_w - margin - disc_radius
        self.cy = screen_h - margin - disc_radius

    def draw(self, screen: pygame.Surface, player,
             entities: Iterable, stations: Iterable, pois: Iterable = ()):
        """
        Desenha disco, anéis, player no centro e blips.

        `pois` (opcional) = POIs JÁ descobertos (ADR 011) — o fog-of-war é
        responsabilidade do chamador; o radar só desenha o que recebe.
        Estações já vêm via `stations`, então o chamador deve filtrar POIs
        de kind "station" para não duplicar o blip.
        """
        if player is None:
            return

        ppos = player.position
        pfac = getattr(player, "faction", "Independent")

        # --- Disco de fundo + anéis -----------------------------------
        disc = pygame.Surface((self.disc_radius * 2, self.disc_radius * 2),
                              pygame.SRCALPHA)
        c = self.disc_radius
        pygame.draw.circle(disc, (10, 25, 30, 150), (c, c), self.disc_radius)
        pygame.draw.circle(disc, (40, 120, 130, 200), (c, c), self.disc_radius, 1)
        pygame.draw.circle(disc, (30, 90, 100, 120), (c, c), self.disc_radius // 2, 1)
        # Cruz central
        pygame.draw.line(disc, (30, 90, 100, 90), (c, c - 4), (c, c + 4))
        pygame.draw.line(disc, (30, 90, 100, 90), (c - 4, c), (c + 4, c))
        screen.blit(disc, (self.cx - c, self.cy - c))

        # --- Estações (verde) -----------------------------------------
        for st in stations:
            self._blit_blip(screen, ppos, getattr(st, "position", [0, 0]),
                            COLOR_STATION, square=True)

        # --- POIs descobertos (violeta) -------------------------------
        for poi in pois:
            self._blit_blip(screen, ppos, getattr(poi, "position", [0, 0]),
                            COLOR_POI)

        # --- Naves (cor por relação) ----------------------------------
        for ent in entities:
            if getattr(ent, "is_player", False):
                continue
            efac = getattr(ent, "faction", "Independent")
            color = _RELATION_COLOR[relation(pfac, efac)]
            self._blit_blip(screen, ppos, getattr(ent, "position", [0, 0]), color)

        # --- Player no centro -----------------------------------------
        pygame.draw.circle(screen, COLOR_PLAYER, (self.cx, self.cy), 3)

    def _blit_blip(self, screen, player_pos, target_pos, color, square=False):
        dx, dy, on_edge, in_range = radar_project(
            player_pos, target_pos, self.world_range, self.disc_radius)
        x = int(self.cx + dx)
        y = int(self.cy + dy)
        if on_edge:
            # Fora do alcance: blip atenuado (dá direção sem poluir).
            faded = tuple(int(ch * 0.55) for ch in color)
            if square:
                pygame.draw.rect(screen, faded, (x - 2, y - 2, 4, 4), 1)
            else:
                pygame.draw.circle(screen, faded, (x, y), 2, 1)
        else:
            if square:
                pygame.draw.rect(screen, color, (x - 2, y - 2, 4, 4))
            else:
                pygame.draw.circle(screen, color, (x, y), 2)
