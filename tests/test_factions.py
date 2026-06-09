"""
Teste de Facções e Reputação (sistema multi-eixo atual).

Exercita a API VIVA do FactionManager (reputation_axes multi-eixo), e não a
antiga reputação de eixo único (player_reputation/get_reputation_level), que
foi substituída. Foca em pontos NÃO cobertos por test_reputation_v2.py:
  1. Evento UPDATE_REPUTATION impactando múltiplos eixos de uma vez.
  2. Clamp dos eixos em [-100, 100] via update_axis.
  3. Permissão de acoplagem (can_dock) sensível a aggression/trust.
  4. Flags históricas.
  5. Round-trip de serialização (get_save_data / load_save_data).

Headless, sem pygame. Roda direto: python tests/test_factions.py
"""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.data_loader import DataLoader
from systems.faction_manager import FactionManager
from core.event_bus import bus


def test_faction_system():
    print("--- Iniciando Teste de Facções e Reputação (multi-eixo) ---")

    # Bus é singleton global: limpar listeners de testes anteriores.
    bus._listeners.clear()

    # 1. Setup
    loader = DataLoader(data_dir="data")
    faction_mgr = FactionManager()
    factions_data = loader.load_json("factions.json")["factions"]
    faction_mgr.setup_factions(factions_data)

    # 2. Estado inicial: todos os eixos presentes
    uh_axes = faction_mgr.reputation_axes["United Humans"]
    print(f"\nEixos iniciais (United Humans): {uh_axes}")
    for axis in ("trust", "aggression", "economic_value",
                 "political_alignment", "technological_alignment"):
        assert axis in uh_axes, f"Eixo ausente: {axis}"

    # 3. Evento UPDATE_REPUTATION impacta múltiplos eixos de uma só vez
    trust0 = uh_axes["trust"]
    econ0 = uh_axes["economic_value"]
    bus.emit("UPDATE_REPUTATION", {
        "faction": "United Humans",
        "impact": {"trust": 10, "economic_value": 25},
    })
    assert uh_axes["trust"] == trust0 + 10, "trust não atualizou via evento"
    assert uh_axes["economic_value"] == econ0 + 25, "economic_value não atualizou"
    print(f"Após UPDATE_REPUTATION (+10 trust, +25 econ): {uh_axes}")

    # 4. Clamp em [-100, 100]
    faction_mgr.update_axis("United Humans", "trust", 1000)
    assert uh_axes["trust"] == 100, "trust deveria saturar em 100"
    faction_mgr.update_axis("United Humans", "trust", -1000)
    assert uh_axes["trust"] == -100, "trust deveria saturar em -100"
    print(f"Clamp OK: trust saturou em {uh_axes['trust']}")

    # 5. Permissão de acoplagem (can_dock)
    # Reset trust para neutro e garantir baixa agressão -> pode acoplar.
    faction_mgr.update_axis("United Humans", "trust", 100)  # de -100 para 0
    faction_mgr.reputation_axes["United Humans"]["aggression"] = 0
    assert faction_mgr.can_dock("United Humans"), "deveria permitir acoplagem"
    faction_mgr.update_axis("United Humans", "aggression", 60)  # > 50
    assert not faction_mgr.can_dock("United Humans"), "agressão alta deveria bloquear"
    print("can_dock sensível a aggression: OK")

    # 6. Flags históricas (permanentes, sem duplicar)
    faction_mgr.add_historical_flag("HERO_OF_SOL")
    faction_mgr.add_historical_flag("HERO_OF_SOL")  # idempotente
    assert "HERO_OF_SOL" in faction_mgr.historical_flags
    assert len(faction_mgr.historical_flags) == 1, "flag não deveria duplicar"
    print(f"Flags históricas: {faction_mgr.historical_flags}")

    # 7. Round-trip de serialização
    save_data = faction_mgr.get_save_data()
    new_mgr = FactionManager()
    new_mgr.load_save_data(save_data)
    assert new_mgr.reputation_axes == faction_mgr.reputation_axes, "axes não restaurados"
    assert new_mgr.historical_flags == faction_mgr.historical_flags, "flags não restauradas"
    print("Round-trip get_save_data/load_save_data: OK")

    print("\nTeste de Facções: OK")


if __name__ == "__main__":
    test_faction_system()
