"""
Teste headless do SupercruiseManager (ADR 010) — SEM pygame.

Valida a lógica pura da viagem rápida:
  1. can_enter: False com massa dentro de min_entry_distance; True longe.
  2. step acelera o player ao longo da proa (velocidade cresce até max_speed).
  3. A posição integra na direção da proa (anda muito mais que no voo normal).
  4. Drop por massa: estação à frente → em algum step drop=True e drop_pos
     a ~exit_offset da estação.
  5. drop_pos nunca cai dentro do docking_radius (não auto-acopla).
  6. Idempotência: chamar step após o drop não crasha.
"""
import os
import sys
import math

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from systems.supercruise_manager import SupercruiseManager
from entities.ship import Ship

DT = 1.0 / 60.0

# Seção de balance fixa (independe do disco, para o teste ser determinístico).
SC = {
    "speed_mult": 40.0,
    "max_speed": 6000.0,
    "accel": 4000.0,
    "spool_up_s": 2.0,
    "drop_radius": 320.0,
    "exit_offset": 260.0,
    "min_entry_distance": 360.0,
}


class FakeStation:
    """Massa mínima: só o que o manager lê."""
    def __init__(self, position, docking_radius=180.0):
        self.position = list(position)
        self.docking_radius = docking_radius


def make_ship(pos=(0.0, 0.0), rotation=0.0):
    s = Ship(
        id="player", name="Skiff", ship_class="Small", model_id="starter_skiff",
        mass=120, energy_capacity=100, heat_dissipation=8,
        max_hp=80, current_hp=80, max_shields=100, current_shields=100,
        is_player=True, faction="United Humans",
    )
    s.position = list(pos)
    s.rotation = rotation
    s.velocity = [0.0, 0.0]
    return s


def main():
    print("=" * 60)
    print("Teste de Supercruise (ADR 010)")
    print("=" * 60)

    assert "pygame" not in sys.modules, "supercruise_manager não deve importar pygame"
    print("\n[0] Nenhum import de pygame  ✓")

    mgr = SupercruiseManager(SC)

    # ------------------------------------------------------------------
    # 1) can_enter
    # ------------------------------------------------------------------
    print("\n[1] can_enter perto/longe de massa")
    player_pos = [0.0, 0.0]
    near = FakeStation([200.0, 0.0])   # dist 200 < min_entry (360)
    far = FakeStation([5000.0, 0.0])   # dist 5000 > min_entry
    assert mgr.can_enter(player_pos, [near]) is False
    assert mgr.can_enter(player_pos, [far]) is True
    assert mgr.can_enter(player_pos, []) is True
    print("  ✓ False com massa a 200u; True a 5000u e sem massas")

    # ------------------------------------------------------------------
    # 2) step acelera até max_speed
    # ------------------------------------------------------------------
    print("\n[2] step acelera ao longo da proa até max_speed")
    ship = make_ship(pos=(0.0, 0.0), rotation=0.0)  # proa = +X
    far_mass = [FakeStation([1e9, 1e9])]            # massa irrelevante (longe)
    speeds = []
    for _ in range(10):
        r = mgr.step(ship, far_mass, DT)
        speeds.append(r["speed"])
    assert speeds[-1] > speeds[0] > 0, speeds
    # Velocidade aponta para +X (proa)
    assert ship.velocity[0] > 0 and abs(ship.velocity[1]) < 1e-9
    print(f"  ✓ velocidade cresce: {speeds[0]:.1f} → {speeds[-1]:.1f} u/s (proa +X)")

    # Satura em max_speed após muitos frames
    for _ in range(600):
        mgr.step(ship, far_mass, DT)
    sat = math.hypot(*ship.velocity)
    assert abs(sat - SC["max_speed"]) < 1e-6, sat
    print(f"  ✓ satura em max_speed={sat:.1f} u/s")

    # ------------------------------------------------------------------
    # 3) posição integra na direção da proa (anda muito)
    # ------------------------------------------------------------------
    print("\n[3] posição integra muito mais que voo normal")
    ship = make_ship(pos=(0.0, 0.0), rotation=0.0)
    for _ in range(60):  # 1 segundo
        mgr.step(ship, far_mass, DT)
    dist_sc = ship.position[0]
    # Voo normal (Skiff): velocidade de cruzeiro ~150 u/s → ~150 em 1s.
    assert dist_sc > 1000.0, f"supercruise andou só {dist_sc:.0f}u em 1s"
    assert ship.position[1] == 0.0  # reto na proa
    print(f"  ✓ andou {dist_sc:.0f}u em 1s (voo normal cruzaria ~150u)")

    # ------------------------------------------------------------------
    # 4) Drop por massa à frente
    # ------------------------------------------------------------------
    print("\n[4] drop automático ao chegar perto da estação")
    ship = make_ship(pos=(0.0, 0.0), rotation=0.0)  # proa +X
    station = FakeStation([20000.0, 0.0], docking_radius=180.0)
    dropped = None
    for i in range(100000):
        r = mgr.step(ship, [station], DT)
        if r["drop"]:
            dropped = r
            break
    assert dropped is not None, "nunca deu drop antes de cruzar a estação"
    dp = dropped["drop_pos"]
    dist_to_station = math.hypot(dp[0] - station.position[0], dp[1] - station.position[1])
    assert abs(dist_to_station - SC["exit_offset"]) < 1e-6, dist_to_station
    print(f"  ✓ drop em frame {i}: drop_pos a {dist_to_station:.1f}u da estação "
          f"(exit_offset={SC['exit_offset']:.0f})")

    # ------------------------------------------------------------------
    # 5) drop_pos FORA do docking_radius (não auto-acopla)
    # ------------------------------------------------------------------
    print("\n[5] drop_pos nunca dentro do docking_radius")
    # Testa de várias direções de aproximação.
    for ang in (0, 45, 90, 137, 200, 300):
        sh = make_ship(pos=(0.0, 0.0), rotation=ang)
        fwd = sh.get_forward_vector()
        st = FakeStation([fwd[0] * 8000, fwd[1] * 8000], docking_radius=180.0)
        res = None
        for _ in range(100000):
            res = mgr.step(sh, [st], DT)
            if res["drop"]:
                break
        assert res and res["drop"], f"sem drop no ângulo {ang}"
        dp = res["drop_pos"]
        d = math.hypot(dp[0] - st.position[0], dp[1] - st.position[1])
        assert d > st.docking_radius, \
            f"drop_pos dentro do docking_radius no ângulo {ang}: {d:.1f} <= {st.docking_radius}"
    print(f"  ✓ exit_offset ({SC['exit_offset']:.0f}) > docking_radius (180) "
          f"em todas as direções testadas")

    # ------------------------------------------------------------------
    # 6) Idempotência após drop (não crasha)
    # ------------------------------------------------------------------
    print("\n[6] step após o drop não crasha")
    # Reposiciona como o main_pygame faria, zera velocidade, chama step de novo.
    ship.position = list(dropped["drop_pos"])
    ship.velocity = [0.0, 0.0]
    r2 = mgr.step(ship, [station], DT)
    assert isinstance(r2, dict) and "drop" in r2
    # Como já está dentro do drop_radius, deve sinalizar drop de novo (idempotente).
    assert r2["drop"] is True
    print("  ✓ step pós-drop devolve dict válido (drop=True, sem crash)")

    print("\nTeste de supercruise: OK")


if __name__ == "__main__":
    main()
