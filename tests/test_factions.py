"""
Teste de facções e reputação multi-eixo (headless, sem pygame).

Reescrito contra a API atual do FactionManager (sistema multi-eixo). A API
antiga (`player_reputation`, `get_reputation_level`, `add_reputation`,
níveis de reputação nomeados) NÃO existe mais por decisão de design — o
modelo atual usa `reputation_axes` (trust/aggression/economic_value/
political_alignment/technological_alignment), -100..100 por eixo.

Cobre a intenção original (estado inicial, mudança via evento, persistência),
mais o que o modelo atual acrescenta: market multiplier, can_dock e flags
históricas. Cada teste limpa o bus no início (sem dependência de ordem).
"""
import os
import sys
import json

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.event_bus import bus
from systems.faction_manager import FactionManager


def _load_factions_data():
    path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                        "data", "factions.json")
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)["factions"]


def main():
    print("=" * 60)
    print("Teste de Facções e Reputação Multi-eixo")
    print("=" * 60)

    bus._listeners.clear()

    factions_data = _load_factions_data()
    mgr = FactionManager()
    mgr.setup_factions(factions_data)

    # ------------------------------------------------------------------
    # 1) Estado inicial (lê reputation_axes, conforme data/factions.json)
    # ------------------------------------------------------------------
    print("\n[1] Estado inicial dos eixos")
    uh = mgr.reputation_axes["United Humans"]
    pir = mgr.reputation_axes["Pirates"]
    marth = mgr.reputation_axes["Marth"]
    assert uh["trust"] == 10, uh
    assert uh["economic_value"] == 5, uh
    assert uh["political_alignment"] == 20, uh
    assert pir["trust"] == -50, pir
    assert pir["aggression"] == 30, pir
    assert marth["technological_alignment"] == 50, marth
    print("  ✓ trust/aggression/econ/político/tecnológico conferem com o JSON")

    # ------------------------------------------------------------------
    # 2) UPDATE_REPUTATION com impacto multi-eixo + limites -100..100
    # ------------------------------------------------------------------
    print("\n[2] UPDATE_REPUTATION (impacto multi-eixo)")
    bus.emit("UPDATE_REPUTATION", {
        "faction": "United Humans",
        "impact": {"trust": 15, "economic_value": -3},
    })
    assert uh["trust"] == 25, uh        # 10 + 15
    assert uh["economic_value"] == 2, uh  # 5 - 3
    print(f"  ✓ merge por eixo: trust {uh['trust']}, econ {uh['economic_value']}")

    # Limites: satura em +100 e -100, não estoura
    mgr.update_axis("United Humans", "trust", 1000)
    assert uh["trust"] == 100, uh
    mgr.update_axis("Pirates", "trust", -1000)
    assert pir["trust"] == -100, pir
    print("  ✓ saturação em [-100, 100]")

    # ------------------------------------------------------------------
    # 3) get_market_multiplier (faixa 0.8–1.5)
    # ------------------------------------------------------------------
    print("\n[3] get_market_multiplier")
    for fname in ("United Humans", "Pirates", "Marth"):
        m = mgr.get_market_multiplier(fname)
        assert 0.8 <= m <= 1.5, (fname, m)
    print("  ✓ multiplicador sempre dentro de [0.8, 1.5]")

    # ------------------------------------------------------------------
    # 4) can_dock (aggression > 50 OU trust < -50 bloqueia)
    # ------------------------------------------------------------------
    print("\n[4] can_dock")
    # Pirates está com trust=-100 (< -50) → bloqueado
    assert mgr.can_dock("Pirates") is False
    # United Humans está saudável → liberado
    assert mgr.can_dock("United Humans") is True
    # Bloqueio por agressão: empurra Marth para aggression > 50
    mgr.update_axis("Marth", "aggression", 60)
    assert mgr.can_dock("Marth") is False
    print("  ✓ bloqueio por trust < -50 e por aggression > 50")

    # ------------------------------------------------------------------
    # 5) add_historical_flag (set, emite FLAG_ADDED, idempotente)
    # ------------------------------------------------------------------
    print("\n[5] add_historical_flag")
    flag_events = []
    bus.subscribe("FLAG_ADDED", lambda d: flag_events.append(d))
    bus.emit("ADD_HISTORICAL_FLAG", "destruiu_frota_pirata")
    assert "destruiu_frota_pirata" in mgr.historical_flags
    assert len(flag_events) == 1
    # Idempotente: re-adicionar não duplica nem reemite
    bus.emit("ADD_HISTORICAL_FLAG", "destruiu_frota_pirata")
    assert len(mgr.historical_flags) == 1
    assert len(flag_events) == 1
    print("  ✓ flag adicionada uma vez, FLAG_ADDED emitido uma vez")

    # ------------------------------------------------------------------
    # 6) Round-trip de persistência
    # ------------------------------------------------------------------
    print("\n[6] Round-trip get_save_data → load_save_data")
    save = mgr.get_save_data()
    assert "reputation_axes" in save
    assert "historical_flags" in save
    assert "diplomacy" in save

    new_mgr = FactionManager()
    new_mgr.load_save_data(save)
    assert new_mgr.reputation_axes["United Humans"]["trust"] == 100
    assert new_mgr.reputation_axes["Pirates"]["trust"] == -100
    assert "destruiu_frota_pirata" in new_mgr.historical_flags
    assert new_mgr.diplomacy["United Humans"]["Pirates"] == "HOSTILE"
    print("  ✓ eixos, flags e diplomacia restaurados idênticos")

    print("\nTeste de facções: OK")


if __name__ == "__main__":
    main()
