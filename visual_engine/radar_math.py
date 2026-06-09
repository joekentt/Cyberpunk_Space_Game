"""
Matemática pura do radar (ver ADR 008) — SEM pygame, testável headless.

A classe `Radar` (em `radar.py`) só desenha; toda a projeção mundo→disco fica
aqui para ser coberta por `tests/test_radar.py` sem abrir janela.

Convenção de orientação: **norte do radar = +Y do mundo** (norte fixo do
mundo, não alinhado à proa). Escolha deliberada por estabilidade visual: o
disco não gira com a nave, então os blips não "deslizam" ao manobrar.
"""
import math
from typing import Tuple


def radar_project(player_pos, target_pos, world_range: float, disc_radius: float
                  ) -> Tuple[float, float, bool, bool]:
    """
    Projeta a posição de um alvo no disco do radar, relativo ao player.

    Retorna `(dx, dy, on_edge, in_range)` em pixels **relativos ao centro do
    disco** (dx para a direita, dy para baixo na tela):
      - alvo na mesma posição do player → (0, 0, False, True)
      - alvo dentro do alcance → blip proporcional, in_range=True
      - alvo além do alcance → blip clampado na borda
        (|(dx,dy)| == disc_radius), on_edge=True, in_range=False

    `world_range` é o alcance do radar em unidades de mundo; `disc_radius`
    é o raio do disco em pixels.
    """
    rel_x = target_pos[0] - player_pos[0]
    rel_y = target_pos[1] - player_pos[1]
    dist = math.hypot(rel_x, rel_y)

    if dist <= 1e-9:
        return (0.0, 0.0, False, True)

    in_range = dist <= world_range
    scale = disc_radius / world_range
    rx = rel_x * scale
    ry = rel_y * scale

    if not in_range:
        # Clampa na borda do disco mantendo a direção.
        norm = disc_radius / dist
        rx = rel_x * norm
        ry = rel_y * norm
        return (rx, ry, True, False)

    return (rx, ry, False, True)
