"""
Teste headless da matemática do mapa estelar (ADR 011) — SEM pygame.

Valida `visual_engine/starmap_math.py`:
  1. compute_bounds: caixa correta com margem; casos degenerados (vazio,
     um ponto) não produzem largura/altura zero.
  2. world_to_map: POI em coordenada conhecida cai no pixel esperado
     (escala uniforme, conteúdo centralizado).
  3. Clamp: ponto fora dos bounds fica dentro do rect.
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from visual_engine.starmap_math import compute_bounds, world_to_map


def main():
    print("=" * 60)
    print("Teste de Starmap (matemática — ADR 011)")
    print("=" * 60)

    assert "pygame" not in sys.modules, "starmap_math não deve importar pygame"
    print("\n[0] Nenhum import de pygame  ✓")

    # ------------------------------------------------------------------
    # 1) compute_bounds
    # ------------------------------------------------------------------
    print("\n[1] compute_bounds")
    b = compute_bounds([(0, 0), (100, 50)], margin=10)
    assert b == (-10, -10, 110, 60), b
    print(f"  ✓ pontos (0,0)/(100,50) margem 10 → {b}")

    # Vazio → caixa unitária, nunca degenerada
    b_empty = compute_bounds([], margin=0)
    assert b_empty[2] > b_empty[0] and b_empty[3] > b_empty[1]
    # Um único ponto → engordada
    b_one = compute_bounds([(5, 5)], margin=0)
    assert b_one[2] - b_one[0] > 0 and b_one[3] - b_one[1] > 0
    # Pontos colineares no eixo Y → largura engordada
    b_line = compute_bounds([(7, 0), (7, 100)], margin=0)
    assert b_line[2] - b_line[0] > 0
    print("  ✓ casos degenerados (vazio/1 ponto/colinear) nunca têm lado zero")

    # ------------------------------------------------------------------
    # 2) world_to_map — projeção conhecida
    # ------------------------------------------------------------------
    print("\n[2] world_to_map em coordenadas conhecidas")
    # Mundo 200×100, rect 400×200 → mesma proporção, escala 2, sem offset.
    bounds = (0.0, 0.0, 200.0, 100.0)
    rect = (0.0, 0.0, 400.0, 200.0)
    assert world_to_map((0, 0), bounds, rect) == (0.0, 0.0)
    assert world_to_map((200, 100), bounds, rect) == (400.0, 200.0)
    assert world_to_map((100, 50), bounds, rect) == (200.0, 100.0)
    print("  ✓ escala 2× exata: cantos e centro caem nos pixels esperados")

    # Proporções diferentes: mundo 100×100 num rect 400×200 → escala
    # uniforme 2 (limitada pela altura), centralizado em X (offset 100).
    bounds_sq = (0.0, 0.0, 100.0, 100.0)
    px, py = world_to_map((0, 0), bounds_sq, rect)
    assert (px, py) == (100.0, 0.0), (px, py)
    px, py = world_to_map((100, 100), bounds_sq, rect)
    assert (px, py) == (300.0, 200.0), (px, py)
    px, py = world_to_map((50, 50), bounds_sq, rect)
    assert (px, py) == (200.0, 100.0), (px, py)
    print("  ✓ aspecto preservado: conteúdo quadrado centralizado no rect largo")

    # Rect com offset de origem
    rect_off = (60.0, 90.0, 400.0, 200.0)
    px, py = world_to_map((100, 50), bounds, rect_off)
    assert (px, py) == (260.0, 190.0), (px, py)
    print("  ✓ offset do rect aplicado (origem 60,90)")

    # ------------------------------------------------------------------
    # 3) Clamp aos limites
    # ------------------------------------------------------------------
    print("\n[3] Clamp de pontos fora dos bounds")
    for outside in [(-500, 50), (700, 50), (100, -500), (100, 900),
                    (-500, -500), (9999, 9999)]:
        px, py = world_to_map(outside, bounds, rect)
        assert 0.0 <= px <= 400.0 and 0.0 <= py <= 200.0, (outside, px, py)
    print("  ✓ 6 pontos externos clampados dentro do rect")

    print("\nTeste de starmap: OK")


if __name__ == "__main__":
    main()
