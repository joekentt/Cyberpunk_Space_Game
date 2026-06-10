"""
StarmapUI — tela de mapa do setor (game_state "starmap", ADR 011).

Mostra o setor em escala reduzida com fog-of-war: só POIs descobertos
aparecem. O jogo fica congelado enquanto o mapa está aberto (como o menu de
pausa). A matemática de projeção vive em `starmap_math.py` (pura); esta
classe só desenha.

Os limites do mapa são computados de TODOS os POIs (não só descobertos) para
a moldura não "pular" a cada descoberta — não vaza nada além do tamanho do
setor.
"""
import math
import pygame
from typing import List

from visual_engine.starmap_math import compute_bounds, world_to_map

# Cores por tipo de POI (alinhadas ao radar/HUD).
KIND_COLORS = {
    "station":        (60, 220, 120),
    "asteroid_field": (200, 160, 90),
    "signal":         (210, 200, 90),
    "derelict":       (200, 90, 90),
}
KIND_LABELS = {
    "station":        "Estação",
    "asteroid_field": "Campo de asteroides",
    "signal":         "Sinal não identificado",
    "derelict":       "Destroços",
}
COLOR_PLAYER = (255, 255, 255)


class StarmapUI:
    def __init__(self, width: int, height: int):
        self.W = width
        self.H = height
        self.selection = 0
        self.font_title = pygame.font.SysFont("Consolas", 24, bold=True)
        self.font_body = pygame.font.SysFont("Consolas", 14)
        self.font_small = pygame.font.SysFont("Consolas", 12)
        # Retângulo do mapa dentro do painel.
        self.map_rect = (60, 90, width - 120, height - 210)

    def open(self):
        self.selection = 0

    # ---- Input ---------------------------------------------------------

    def handle_event(self, ev, discovered_count: int):
        """↑↓ navegam a seleção entre POIs descobertos."""
        if ev.type != pygame.KEYDOWN or discovered_count == 0:
            return
        if ev.key == pygame.K_UP:
            self.selection = (self.selection - 1) % discovered_count
        elif ev.key == pygame.K_DOWN:
            self.selection = (self.selection + 1) % discovered_count

    # ---- Render --------------------------------------------------------

    def draw(self, screen: pygame.Surface, player, pois: List):
        """`pois` = todos os POIs do setor (fog é aplicado aqui)."""
        # Painel de fundo
        overlay = pygame.Surface((self.W, self.H), pygame.SRCALPHA)
        overlay.fill((4, 8, 16, 235))
        screen.blit(overlay, (0, 0))
        pygame.draw.rect(screen, (0, 150, 200),
                         (20, 20, self.W - 40, self.H - 40), width=1)

        title = self.font_title.render("MAPA DO SETOR", True, (0, 220, 255))
        screen.blit(title, (40, 36))

        discovered = [p for p in pois if p.discovered]
        hidden_n = len(pois) - len(discovered)
        sub = self.font_small.render(
            f"{len(discovered)} localizações conhecidas · "
            f"{hidden_n} sinais não mapeados",
            True, (140, 170, 200))
        screen.blit(sub, (40, 66))

        # Moldura do mapa
        mx, my, mw, mh = self.map_rect
        pygame.draw.rect(screen, (10, 18, 30), self.map_rect)
        pygame.draw.rect(screen, (40, 90, 110), self.map_rect, width=1)

        # Bounds estáveis: todos os POIs + player.
        pts = [p.position for p in pois]
        if player is not None:
            pts.append(player.position)
        bounds = compute_bounds(pts, margin=300.0)

        if self.selection >= max(1, len(discovered)):
            self.selection = 0

        # POIs descobertos (fog: ocultos não aparecem)
        for i, poi in enumerate(discovered):
            px, py = world_to_map(poi.position, bounds, self.map_rect)
            color = KIND_COLORS.get(poi.kind, (180, 180, 180))
            selected = (i == self.selection)
            if poi.kind == "station":
                pygame.draw.rect(screen, color, (px - 4, py - 4, 8, 8))
            else:
                pygame.draw.circle(screen, color, (int(px), int(py)), 4)
            if selected:
                pygame.draw.circle(screen, (255, 255, 255),
                                   (int(px), int(py)), 9, 1)
            name = self.font_small.render(poi.name, True, color)
            screen.blit(name, (px + 10, py - 7))

        # Player (seta orientada pela proa)
        if player is not None:
            px, py = world_to_map(player.position, bounds, self.map_rect)
            rad = math.radians(player.rotation)
            tip = (px + math.cos(rad) * 9, py + math.sin(rad) * 9)
            left = (px + math.cos(rad + 2.5) * 6, py + math.sin(rad + 2.5) * 6)
            right = (px + math.cos(rad - 2.5) * 6, py + math.sin(rad - 2.5) * 6)
            pygame.draw.polygon(screen, COLOR_PLAYER, (tip, left, right))

        # Painel de detalhes do POI selecionado
        if discovered and player is not None:
            poi = discovered[self.selection]
            dx = poi.position[0] - player.position[0]
            dy = poi.position[1] - player.position[1]
            dist = math.hypot(dx, dy)
            info = (f"▸ {poi.name}  ·  {KIND_LABELS.get(poi.kind, poi.kind)}"
                    f"  ·  {dist:,.0f} u".replace(",", "."))
            txt = self.font_body.render(info, True, (220, 230, 245))
            screen.blit(txt, (60, my + mh + 16))
            hint2 = self.font_small.render(
                "Use o supercruise (J) mirando a proa para viajar até lá.",
                True, (120, 150, 180))
            screen.blit(hint2, (60, my + mh + 40))

        help_txt = self.font_small.render(
            "↑↓ selecionar localização   M ou ESC fechar",
            True, (120, 140, 160))
        screen.blit(help_txt,
                    (self.W // 2 - help_txt.get_width() // 2, self.H - 44))
