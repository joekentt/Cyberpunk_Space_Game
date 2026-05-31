"""
Teste headless do sistema de movimento da nave do jogador.

Valida os thrusters adicionados ao PlayerManager:
  - strafe lateral (Q/E) move perpendicular ao bico SEM girar
  - throttle negativo (S) primeiro freia e depois engata ré
  - hierarquia de empuxo: frente > ré > strafe lateral
"""
import os
import sys
import math

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.event_bus import bus
from systems.player_manager import PlayerManager
from entities.ship import Ship


DT = 1.0 / 60.0


def make_player(rotation: float = 0.0):
    ship = Ship(
        id="player",
        name="Skiff Mk I",
        ship_class="Small",
        model_id="starter_skiff",
        mass=120, energy_capacity=100, heat_dissipation=8,
        max_hp=80, current_hp=80,
        max_shields=100, current_shields=100,
        is_player=True,
        faction="United Humans",
    )
    ship.rotation = rotation
    pm = PlayerManager(ship)
    return ship, pm


def reset(ship, rotation=None):
    ship.velocity[0] = 0.0
    ship.velocity[1] = 0.0
    if rotation is not None:
        ship.rotation = rotation


def speed_of(ship):
    return math.hypot(ship.velocity[0], ship.velocity[1])


def forward_component(ship, fwd):
    return ship.velocity[0] * fwd[0] + ship.velocity[1] * fwd[1]


def speed_from_rest(ship, pm, action, value):
    """Aplica um único input a partir do repouso e mede a velocidade resultante."""
    reset(ship)
    bus.emit("PLAYER_INPUT", {"action": action, "value": value})
    pm.update(DT)
    return speed_of(ship)


def main():
    print("=" * 60)
    print("Teste de Movimento (strafe / ré / hierarquia de empuxo)")
    print("=" * 60)

    ship, pm = make_player(rotation=0.0)

    # ------------------------------------------------------------------
    # 1) Strafe move perpendicular ao bico SEM alterar a rotação
    # ------------------------------------------------------------------
    print("\n[1] Strafe perpendicular sem girar o bico")
    rot = 30.0
    reset(ship, rotation=rot)
    fwd = ship.get_forward_vector()
    rot_before = ship.rotation

    bus.emit("PLAYER_INPUT", {"action": "strafe", "value": 1.0})  # E (direita)
    pm.update(DT)

    dot = forward_component(ship, fwd)
    assert abs(ship.rotation - rot_before) < 1e-9, \
        f"strafe NÃO deve girar o bico (rot {rot_before} -> {ship.rotation})"
    assert speed_of(ship) > 0.0, "strafe deveria gerar velocidade"
    assert abs(dot) < 1e-6, \
        f"velocidade do strafe deveria ser perpendicular ao bico (dot={dot:.6f})"
    print(f"  rotation inalterada: {rot_before}° -> {ship.rotation}°")
    print(f"  velocidade ⟂ ao bico (componente frontal = {dot:.2e} ≈ 0)  ✓")

    # Strafe esquerda (Q) deve apontar para o lado oposto ao strafe direita (E)
    reset(ship, rotation=rot)
    bus.emit("PLAYER_INPUT", {"action": "strafe", "value": 1.0})
    pm.update(DT)
    right_vel = (ship.velocity[0], ship.velocity[1])
    reset(ship, rotation=rot)
    bus.emit("PLAYER_INPUT", {"action": "strafe", "value": -1.0})
    pm.update(DT)
    left_vel = (ship.velocity[0], ship.velocity[1])
    opp_dot = right_vel[0] * left_vel[0] + right_vel[1] * left_vel[1]
    assert opp_dot < 0, "Q e E devem empurrar para lados opostos"
    print("  Q e E empurram para lados opostos  ✓")

    # ------------------------------------------------------------------
    # 2) Segurar S: primeiro freia (vel. frontal+) depois engata ré (vel. frontal-)
    # ------------------------------------------------------------------
    print("\n[2] Segurar S: freia e depois engata a ré")
    reset(ship, rotation=0.0)
    fwd = ship.get_forward_vector()              # [1, 0]
    ship.velocity[0] = 100.0 * fwd[0]            # velocidade frontal positiva
    ship.velocity[1] = 100.0 * fwd[1]
    comp = forward_component(ship, fwd)
    print(f"  velocidade frontal inicial: {comp:.1f}")

    braked = False
    reversed_engaged = False
    prev = comp
    comp_at_cross = None
    for _ in range(2000):
        bus.emit("PLAYER_INPUT", {"action": "thrust", "value": -1.0})
        pm.update(DT)
        comp = forward_component(ship, fwd)
        if 0.0 < comp < prev - 1e-9:
            braked = True            # decrescendo ainda positivo = freando
        if comp < 0.0:
            reversed_engaged = True  # cruzou o ponto morto = ré engatada
            comp_at_cross = comp
            break
        prev = comp

    assert braked, "deveria FREAR primeiro (vel. frontal positiva caindo)"
    assert reversed_engaged, "deveria engatar a RÉ (vel. frontal cruzando para negativa)"
    print(f"  freou a velocidade frontal positiva  ✓")
    print(f"  cruzou o ponto morto: vel. frontal agora {comp_at_cross:.2f} (< 0)  ✓")

    # Continuar em S deve ACELERAR a ré (componente fica mais negativo)
    for _ in range(10):
        bus.emit("PLAYER_INPUT", {"action": "thrust", "value": -1.0})
        pm.update(DT)
    comp_after = forward_component(ship, fwd)
    assert comp_after < comp_at_cross, \
        f"ré deveria acelerar (de {comp_at_cross:.2f} para mais negativo, foi {comp_after:.2f})"
    print(f"  ré acelerando: {comp_at_cross:.2f} -> {comp_after:.2f}  ✓")

    # ------------------------------------------------------------------
    # 3) Hierarquia de empuxo: frente > ré > strafe lateral
    # ------------------------------------------------------------------
    print("\n[3] Hierarquia de empuxo (frente > ré > strafe)")
    reset(ship, rotation=0.0)
    s_front = speed_from_rest(ship, pm, "thrust", 1.0)
    s_rev = speed_from_rest(ship, pm, "thrust", -1.0)
    s_strafe = speed_from_rest(ship, pm, "strafe", 1.0)
    print(f"  frente:  {s_front:.4f} u/s")
    print(f"  ré:      {s_rev:.4f} u/s")
    print(f"  strafe:  {s_strafe:.4f} u/s")
    assert s_front > s_rev > s_strafe, \
        f"esperado frente > ré > strafe, foi {s_front:.4f} / {s_rev:.4f} / {s_strafe:.4f}"
    print("  frente > ré > strafe  ✓")

    print("\nTeste de movimento: OK")


if __name__ == "__main__":
    main()
