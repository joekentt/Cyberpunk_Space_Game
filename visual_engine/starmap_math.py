"""
Matemática pura do mapa estelar (ADR 011) — SEM pygame, testável headless.

A `StarmapUI` (starmap_ui.py) só desenha; toda a projeção mundo→mapa fica
aqui para ser coberta por `tests/test_starmap.py` sem abrir janela.
"""
from typing import Iterable, Sequence, Tuple


def compute_bounds(points: Iterable[Sequence[float]], margin: float = 0.0
                   ) -> Tuple[float, float, float, float]:
    """
    Caixa (min_x, min_y, max_x, max_y) que contém todos os pontos, com
    `margin` extra em cada lado. Sem pontos → caixa unitária em torno da
    origem. Caixa degenerada (1 ponto / pontos colineares) é engordada para
    nunca ter largura/altura zero.
    """
    pts = list(points)
    if not pts:
        return (-1.0 - margin, -1.0 - margin, 1.0 + margin, 1.0 + margin)

    min_x = min(p[0] for p in pts)
    min_y = min(p[1] for p in pts)
    max_x = max(p[0] for p in pts)
    max_y = max(p[1] for p in pts)

    if max_x - min_x < 1e-9:
        min_x -= 1.0
        max_x += 1.0
    if max_y - min_y < 1e-9:
        min_y -= 1.0
        max_y += 1.0

    return (min_x - margin, min_y - margin, max_x + margin, max_y + margin)


def world_to_map(pos: Sequence[float],
                 bounds: Tuple[float, float, float, float],
                 rect: Tuple[float, float, float, float]
                 ) -> Tuple[float, float]:
    """
    Projeta um ponto do mundo no retângulo de tela `rect = (x, y, w, h)`,
    preservando a proporção (escala uniforme, conteúdo centralizado).
    Pontos fora dos bounds são CLAMPADOS às bordas do rect.
    """
    min_x, min_y, max_x, max_y = bounds
    rx, ry, rw, rh = rect

    bw = max(max_x - min_x, 1e-9)
    bh = max(max_y - min_y, 1e-9)

    # Escala uniforme (fit) + offsets de centralização.
    scale = min(rw / bw, rh / bh)
    off_x = rx + (rw - bw * scale) / 2.0
    off_y = ry + (rh - bh * scale) / 2.0

    px = off_x + (pos[0] - min_x) * scale
    py = off_y + (pos[1] - min_y) * scale

    # Clamp aos limites do rect.
    px = max(rx, min(rx + rw, px))
    py = max(ry, min(ry + rh, py))
    return (px, py)
