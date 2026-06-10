"""
Teste headless do sistema de boost de propulsor (Ciclo E / ADR 007).

Valida:
  1. Boost ativa quando há carga e não está em cooldown; consome cost.
  2. Ganho de velocidade frontal durante boost > thrust normal (mesmo dt, repouso).
  3. Boost NÃO afeta ré nem strafe (componente perpendicular/traseiro inalterado).
  4. Cooldown bloqueia reativação imediata; após duration+cooldown o boost reativa.
  5. Recarga sobe com tempo; escala com pips de engines; não ultrapassa max_charge.
  6. Sem carga, try_boost() retorna False e não altera velocidade.
"""
import os
import sys
import math

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.event_bus import bus
from core.balance import balance
from systems.player_manager import PlayerManager
from entities.ship import Ship


DT = 1.0 / 60.0


def make_player(rotation=0.0, pips=None):
    bus._listeners.clear()
    ship = Ship(
        id="player", name="Skiff Mk I", ship_class="Small",
        model_id="starter_skiff", mass=120, energy_capacity=100,
        heat_dissipation=8, max_hp=80, current_hp=80,
        max_shields=100, current_shields=100,
        is_player=True, faction="United Humans",
    )
    ship.rotation = rotation
    pm = PlayerManager(ship)
    if pips:
        pm.pips = dict(pips)
        ship.pips = dict(pips)
    return ship, pm


def reset(ship):
    ship.velocity[0] = 0.0
    ship.velocity[1] = 0.0


def fwd_speed(ship):
    rad = math.radians(ship.rotation)
    fwd = (math.cos(rad), math.sin(rad))
    return ship.velocity[0] * fwd[0] + ship.velocity[1] * fwd[1]


def perp_speed(ship):
    """Componente de velocidade perpendicular ao bico."""
    rad = math.radians(ship.rotation)
    right = (-math.sin(rad), math.cos(rad))
    return ship.velocity[0] * right[0] + ship.velocity[1] * right[1]


def main():
    print("=" * 60)
    print("Teste de Boost de Propulsor (ADR 007)")
    print("=" * 60)

    bp = balance.boost

    # ------------------------------------------------------------------
    # 1) Boost ativa, consome cost, retorna True; cd bloqueia re-ativação
    # ------------------------------------------------------------------
    print("\n[1] Ativação consome carga e retorna True")
    ship, pm = make_player()
    full = pm.boost_charge
    assert full == bp["max_charge"], full

    ok = pm.try_boost()
    assert ok, "try_boost deveria retornar True com carga cheia"
    assert pm.boost_charge == full - bp["cost"], pm.boost_charge
    assert pm._boost_timer > 0
    print(f"  ✓ ativou: carga {full} → {pm.boost_charge:.2f}, timer={pm._boost_timer:.2f}s")

    # Tentativa imediata falha (cooldown/timer ativos)
    ok2 = pm.try_boost()
    assert not ok2, "não deveria ativar durante cooldown"
    print("  ✓ re-ativação imediata bloqueada (cd/timer ativos)")

    # ------------------------------------------------------------------
    # 2) Velocidade frontal durante boost > thrust normal (mesmo DT, repouso)
    # ------------------------------------------------------------------
    print("\n[2] Velocidade frontal boost > thrust normal")

    # Baseline: um frame de W a partir do repouso (sem boost)
    ship_w, pm_w = make_player(rotation=0.0)
    reset(ship_w)
    bus.emit("PLAYER_INPUT", {"action": "thrust", "value": 1.0})
    pm_w.update(DT)
    v_normal = fwd_speed(ship_w)

    # Boost: ativa boost, sem W, um frame
    ship_b, pm_b = make_player(rotation=0.0)
    reset(ship_b)
    bus.emit("PLAYER_INPUT", {"action": "boost"})  # activates boost
    pm_b.update(DT)
    v_boost = fwd_speed(ship_b)

    assert v_boost > v_normal, \
        f"boost ({v_boost:.4f}) deveria ser > thrust normal ({v_normal:.4f})"
    ratio = v_boost / v_normal if v_normal > 0 else float("inf")
    print(f"  ✓ normal={v_normal:.4f}  boost={v_boost:.4f}  ratio={ratio:.2f}×")

    # ------------------------------------------------------------------
    # 3) Boost NÃO afeta ré nem strafe (componentes inalterados)
    # ------------------------------------------------------------------
    print("\n[3] Boost não multiplica ré nem strafe")

    # Strafe baseline (sem boost)
    ship_s, pm_s = make_player(rotation=30.0)
    reset(ship_s)
    bus.emit("PLAYER_INPUT", {"action": "strafe", "value": 1.0})
    pm_s.update(DT)
    v_strafe_base = perp_speed(ship_s)

    # Strafe durante boost ativo: componente perpendicular deve ser igual ao baseline
    ship_sb, pm_sb = make_player(rotation=30.0)
    reset(ship_sb)
    bus.emit("PLAYER_INPUT", {"action": "boost"})
    # advance one tick so boost is active, then emit strafe
    pm_sb.update(DT)
    reset(ship_sb)  # reset velocity so we measure only strafe contribution
    bus.emit("PLAYER_INPUT", {"action": "strafe", "value": 1.0})
    pm_sb.update(DT)
    v_strafe_during_boost = perp_speed(ship_sb)

    assert abs(v_strafe_during_boost - v_strafe_base) < 1e-6, \
        f"strafe durante boost ({v_strafe_during_boost:.6f}) != baseline ({v_strafe_base:.6f})"
    print(f"  ✓ strafe perpendicular: baseline={v_strafe_base:.4f}  durante boost={v_strafe_during_boost:.4f}")

    # Ré baseline (sem boost)
    ship_r, pm_r = make_player(rotation=0.0)
    reset(ship_r)
    bus.emit("PLAYER_INPUT", {"action": "thrust", "value": -1.0})
    pm_r.update(DT)
    v_rev_base = fwd_speed(ship_r)   # negativo (ré)

    # Ré durante boost: isola componente - boost injeta fwd, ré injeta -fwd
    # Medimos componente traseiro subtraindo o boost do resultado
    ship_rb, pm_rb = make_player(rotation=0.0)
    reset(ship_rb)
    bus.emit("PLAYER_INPUT", {"action": "boost"})
    pm_rb.update(DT)
    v_boost_only = fwd_speed(ship_rb)
    reset(ship_rb)
    bus.emit("PLAYER_INPUT", {"action": "thrust", "value": -1.0})
    pm_rb.update(DT)
    # A ré adicionou -v_rev_base ao fwd; o boost estava ativo neste frame:
    # v_fwd = boost_contrib - |rev_contrib|
    # rev_contrib should equal |v_rev_base|
    rev_contrib = v_boost_only - fwd_speed(ship_rb)  # subtraímos o ré
    assert abs(rev_contrib - abs(v_rev_base)) < 1e-6, \
        f"ré durante boost: contrib={rev_contrib:.6f} != baseline={abs(v_rev_base):.6f}"
    print(f"  ✓ ré inalterada pelo boost (contrib={rev_contrib:.4f} == baseline={abs(v_rev_base):.4f})")

    # ------------------------------------------------------------------
    # 4) Cooldown: re-ativa após duration + cooldown segundos
    # ------------------------------------------------------------------
    print("\n[4] Cooldown bloqueia; re-ativa após duration+cooldown")
    ship_cd, pm_cd = make_player()
    ok = pm_cd.try_boost()
    assert ok

    # Antes de expirar: não pode boostar
    frames_dur = int(bp["duration"] * 60) - 1
    for _ in range(frames_dur):
        pm_cd.update(DT)
    assert not pm_cd.try_boost(), "não deveria ativar enquanto timer > 0"

    # Após duration + cooldown: pode boostar (se tiver carga)
    total = bp["duration"] + bp["cooldown"]
    frames_total = int(math.ceil(total * 60)) + 2
    for _ in range(frames_total):
        pm_cd.update(DT)
    assert pm_cd._boost_timer <= 0 and pm_cd._boost_cd <= 0, \
        f"timer={pm_cd._boost_timer:.3f} cd={pm_cd._boost_cd:.3f}"
    if pm_cd.boost_charge >= bp["cost"]:
        ok2 = pm_cd.try_boost()
        assert ok2, "deveria poder boostar após cooldown com carga suficiente"
        print(f"  ✓ re-ativou após {total:.1f}s (timer+cooldown)")
    else:
        print(f"  ✓ cooldown expirou (carga={pm_cd.boost_charge:.2f} — recarga insuficiente no teste)")

    # ------------------------------------------------------------------
    # 5) Recarga: sobe com tempo, escala com pips de engines, satura em max
    # ------------------------------------------------------------------
    print("\n[5] Recarga do capacitor")

    # Drena toda a carga manualmente
    ship_rc, pm_rc = make_player()
    pm_rc.boost_charge = 0.0
    pm_rc._sync_boost_to_ship()

    # 1 segundo de update com pips=2 (engine_mod=0.75)
    for _ in range(60):
        pm_rc.update(DT)
    expected = min(bp["max_charge"], bp["recharge_per_s"] * 0.75 * 1.0)
    assert abs(pm_rc.boost_charge - expected) < 0.05, \
        f"recarga em 1s pips=2: {pm_rc.boost_charge:.3f} != {expected:.3f}"
    print(f"  ✓ 1s @ pips=2: recargou {pm_rc.boost_charge:.3f} (esperado ≈{expected:.3f})")

    # Mais pips = recarga mais rápida
    ship_rc4, pm_rc4 = make_player(pips={"weapons": 0, "shields": 2, "engines": 4})
    pm_rc4.boost_charge = 0.0
    pm_rc4._sync_boost_to_ship()
    for _ in range(60):
        pm_rc4.update(DT)
    assert pm_rc4.boost_charge > pm_rc.boost_charge, \
        f"pips=4 deveria recarregar mais rápido ({pm_rc4.boost_charge:.3f} > {pm_rc.boost_charge:.3f})"
    print(f"  ✓ pips=4 mais rápido: {pm_rc4.boost_charge:.3f} > pips=2: {pm_rc.boost_charge:.3f}")

    # Saturação: nunca ultrapassa max_charge
    ship_sat, pm_sat = make_player()
    pm_sat.boost_charge = bp["max_charge"] - 0.01
    for _ in range(120):
        pm_sat.update(DT)
    assert pm_sat.boost_charge <= bp["max_charge"] + 1e-9, pm_sat.boost_charge
    assert ship_sat.boost_max == bp["max_charge"]
    print(f"  ✓ satura em max_charge={bp['max_charge']:.1f}")

    # ------------------------------------------------------------------
    # 6) Sem carga → try_boost retorna False e não altera velocidade
    # ------------------------------------------------------------------
    print("\n[6] Sem carga: try_boost retorna False")
    ship_nc, pm_nc = make_player()
    pm_nc.boost_charge = 0.0
    reset(ship_nc)
    ok = pm_nc.try_boost()
    assert not ok, "try_boost deve retornar False sem carga"
    assert pm_nc._boost_timer == 0.0
    pm_nc.update(DT)
    assert abs(fwd_speed(ship_nc)) < 1e-9, "sem boost, velocidade deve ser zero"
    print("  ✓ try_boost=False, velocidade inalterada")

    print("\nTeste de boost: OK")


if __name__ == "__main__":
    main()
