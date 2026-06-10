"""
Teste headless do radar de proximidade (ADR 008).

Testa SÓ a matemática (projeção mundo→disco, clamp na borda) e a
classificação de relação de facção — sem importar pygame, sem render.

Valida:
  1. Alvo na mesma posição do player → blip no centro (0,0), in_range.
  2. Alvo dentro do alcance → blip proporcional, in_range=True.
  3. Alvo além do alcance → blip clampado na borda (dist == disc_radius),
     on_edge=True, in_range=False, direção preservada.
  4. relation(): Pirates×United Humans → "hostile"; UH×UH → "ally";
     Independent×UH → "neutral".
"""
import os
import sys
import math

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Garantia explícita: este teste NÃO pode depender de pygame.
import importlib

from visual_engine.radar_math import radar_project
from systems.factions_util import relation, is_hostile, HOSTILITY


def main():
    print("=" * 60)
    print("Teste de Radar (ADR 008)")
    print("=" * 60)

    # Garante que pygame NÃO foi importado pelos módulos sob teste.
    assert "pygame" not in sys.modules, \
        "radar_math/factions_util não devem importar pygame"
    print("\n[0] Nenhum import de pygame nos módulos de matemática  ✓")

    WORLD_RANGE = 2000.0
    DISC = 80.0
    player = [1000.0, 1000.0]

    # ------------------------------------------------------------------
    # 1) Alvo na origem relativa → centro
    # ------------------------------------------------------------------
    print("\n[1] Alvo na mesma posição → centro")
    dx, dy, on_edge, in_range = radar_project(player, list(player), WORLD_RANGE, DISC)
    assert (dx, dy) == (0.0, 0.0), (dx, dy)
    assert not on_edge and in_range
    print(f"  ✓ blip no centro (0,0), in_range={in_range}")

    # ------------------------------------------------------------------
    # 2) Alvo dentro do alcance → proporcional
    # ------------------------------------------------------------------
    print("\n[2] Alvo dentro do alcance → proporcional")
    # 1000 unidades à direita (metade do alcance) → metade do raio do disco
    target = [player[0] + 1000.0, player[1]]
    dx, dy, on_edge, in_range = radar_project(player, target, WORLD_RANGE, DISC)
    assert in_range and not on_edge
    assert abs(dx - DISC * 0.5) < 1e-9, dx     # 1000/2000 * 80 = 40
    assert abs(dy) < 1e-9, dy
    print(f"  ✓ 1000u à direita → dx={dx:.1f} (metade do disco), in_range=True")

    # Diagonal dentro do alcance preserva proporção
    target_d = [player[0] + 600.0, player[1] + 800.0]  # dist=1000 < 2000
    dx, dy, on_edge, in_range = radar_project(player, target_d, WORLD_RANGE, DISC)
    assert in_range and not on_edge
    expected_dist = 1000.0 / WORLD_RANGE * DISC  # 40
    assert abs(math.hypot(dx, dy) - expected_dist) < 1e-9
    print(f"  ✓ diagonal dist=1000u → |blip|={math.hypot(dx, dy):.1f} (proporcional)")

    # ------------------------------------------------------------------
    # 3) Alvo além do alcance → clampado na borda
    # ------------------------------------------------------------------
    print("\n[3] Alvo além do alcance → clampado na borda")
    far = [player[0] + 5000.0, player[1] + 5000.0]  # dist ~7071 >> 2000
    dx, dy, on_edge, in_range = radar_project(player, far, WORLD_RANGE, DISC)
    assert on_edge and not in_range
    dist_on_disc = math.hypot(dx, dy)
    assert abs(dist_on_disc - DISC) < 1e-9, dist_on_disc
    # Direção preservada: 45° (dx == dy, ambos positivos)
    assert dx > 0 and dy > 0 and abs(dx - dy) < 1e-9
    print(f"  ✓ clampado: |blip|={dist_on_disc:.1f} == disc_radius={DISC:.0f}, "
          f"direção 45° preservada (dx={dx:.2f}, dy={dy:.2f})")

    # Caso de fronteira exata: dist == world_range → ainda in_range, na borda
    edge = [player[0] + WORLD_RANGE, player[1]]
    dx, dy, on_edge, in_range = radar_project(player, edge, WORLD_RANGE, DISC)
    assert in_range, "dist == world_range deve contar como dentro"
    assert abs(dx - DISC) < 1e-9
    print(f"  ✓ fronteira exata (dist==range) → dx={dx:.1f}, in_range=True")

    # ------------------------------------------------------------------
    # 4) Classificação de relação
    # ------------------------------------------------------------------
    print("\n[4] relation() por facção")
    assert relation("United Humans", "Pirates") == "hostile"
    assert relation("Pirates", "United Humans") == "hostile"
    assert relation("United Humans", "United Humans") == "ally"
    assert relation("United Humans", "Independent") == "neutral"
    assert relation("Independent", "United Humans") == "neutral"
    print("  ✓ Pirates×UH=hostile, UH×UH=ally, Independent×UH=neutral")

    # is_hostile permanece direcional (semântica da IA preservada)
    assert is_hostile("Pirates", "United Humans") is True
    assert is_hostile("Orcs", "United Humans") is True
    assert is_hostile("United Humans", "Orcs") is False  # direcional!
    assert ("Orcs", "United Humans") in HOSTILITY
    print("  ✓ is_hostile direcional: Orcs→UH=True mas UH→Orcs=False")

    print("\nTeste de radar: OK")


if __name__ == "__main__":
    main()
