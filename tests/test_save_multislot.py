"""
Teste de save multi-slot (Bloco F / ADR 012) — headless, sem pygame.

Valida:
  1. Três estados distintos em três slots: arquivos existem e
     `save_metadata(slot)` devolve piloto/créditos/progresso certos por slot.
  2. `load_game` + `apply_save_payload` de cada slot reconstroem o estado
     correto (créditos e posição por slot).
  3. `delete_save(slot)` remove só aquele slot; os outros permanecem;
     deletar slot inexistente não crasha.
  4. Compatibilidade retro: save no formato "antigo" (v1, sem
     pilot/saved_at/progression) ainda funciona em save_metadata e load.
"""
import os
import sys
import json
import tempfile

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.event_bus import bus
from core.save_manager import SaveManager
from systems.universe_manager import UniverseManager
from systems.player_manager import PlayerManager
from systems.energy_manager import EnergyManager
from systems.mission_manager import MissionManager
from systems.faction_manager import FactionManager
from systems.station_manager import StationManager
from systems.game_state_serializer import build_save_payload, apply_save_payload
from entities.ship import Ship

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def _load_json(*parts):
    with open(os.path.join(ROOT, *parts), "r", encoding="utf-8") as f:
        return json.load(f)


def _make_player(universe, pos, credits):
    template = Ship(
        id="player", name="Skiff", ship_class="Small",
        model_id="starter_skiff", mass=120, energy_capacity=100,
        heat_dissipation=8, max_hp=80, current_hp=80,
        max_shields=100, current_shields=100,
        is_player=True, faction="United Humans", credits=credits,
        hardpoints={"weapon_small": 2},
    )
    pid = universe.spawn_ship(template, pos)
    return pid, universe.entities[pid]


def _fresh_managers(factions_data, templates):
    universe = UniverseManager()
    mission_mgr = MissionManager()
    faction_mgr = FactionManager()
    station_mgr = StationManager(universe)
    faction_mgr.setup_factions(factions_data)
    mission_mgr.set_templates(templates)
    return universe, mission_mgr, faction_mgr, station_mgr


def main():
    print("=" * 60)
    print("Teste de Save Multi-Slot (Bloco F / ADR 012)")
    print("=" * 60)

    factions_data = _load_json("data", "factions.json")["factions"]
    templates = [t for t in _load_json("data", "mission_templates.json")["templates"]
                 if t["type"] == "BOUNTY"]

    save_dir = tempfile.mkdtemp(prefix="space_rpg_multislot_")
    save_mgr = SaveManager(save_dir=save_dir)

    # Três estados distintos: (slot, piloto, créditos, posição, bounties)
    STATES = [
        (1, "Ana",   11111, [100.0, 200.0], 0),
        (2, "Bruno", 22222, [300.0, 400.0], 2),
        (3, "Carla", 33333, [500.0, 600.0], 5),
    ]

    # ------------------------------------------------------------------
    # 1) Salvar três estados em três slots; metadados por slot
    # ------------------------------------------------------------------
    print("\n[1] Três slots gravados; metadados corretos por slot")
    for slot, pilot, credits, pos, bounties in STATES:
        bus._listeners.clear()
        universe, mission_mgr, faction_mgr, _ = _fresh_managers(
            factions_data, templates)
        _, player = _make_player(universe, list(pos), credits)
        payload = build_save_payload(
            player_ship=player,
            pips={"weapons": 2, "shields": 2, "engines": 2},
            mission_mgr=mission_mgr,
            faction_mgr=faction_mgr,
            pilot={"name": pilot},
            progression={"bounties_completed": bounties, "game_completed": False},
        )
        save_mgr.save_game(slot, payload)
        assert os.path.isfile(os.path.join(save_dir, f"save_slot_{slot}.json"))

    for slot, pilot, credits, _, bounties in STATES:
        meta = save_mgr.save_metadata(slot)
        assert meta is not None, f"slot {slot} sem metadados"
        assert meta["pilot_name"] == pilot, meta
        assert meta["credits"] == credits, meta
        assert meta["progress"]["bounties_completed"] == bounties, meta
        assert meta["saved_at"] is not None
        print(f"  ✓ slot {slot}: {meta['pilot_name']}, {meta['credits']} cr, "
              f"{meta['progress']['bounties_completed']} caçadas")

    # Slot vazio → None (sem exceção)
    assert save_mgr.save_metadata(99) is None
    print("  ✓ slot vazio → metadata None")

    # ------------------------------------------------------------------
    # 2) Carregar cada slot reconstrói o estado certo
    # ------------------------------------------------------------------
    print("\n[2] load + apply de cada slot reconstrói o estado certo")
    for slot, pilot, credits, pos, _ in STATES:
        bus._listeners.clear()
        universe, mission_mgr, faction_mgr, station_mgr = _fresh_managers(
            factions_data, templates)
        boot_pid, boot_player = _make_player(universe, [0.0, 0.0], 0)
        player_mgr = PlayerManager(boot_player)
        energy_mgr = EnergyManager(boot_player)

        payload = save_mgr.load_game(slot)
        new_pid = apply_save_payload(
            payload=payload, universe=universe, player_mgr=player_mgr,
            energy_mgr=energy_mgr, mission_mgr=mission_mgr,
            faction_mgr=faction_mgr, station_mgr=station_mgr,
            old_player_id=boot_pid,
        )
        rp = universe.entities[new_pid]
        assert rp.credits == credits, (slot, rp.credits)
        assert abs(rp.position[0] - pos[0]) < 1e-4, (slot, rp.position)
        assert abs(rp.position[1] - pos[1]) < 1e-4, (slot, rp.position)
        assert payload["pilot"]["name"] == pilot
        print(f"  ✓ slot {slot}: créditos {rp.credits}, pos {rp.position}")

    # ------------------------------------------------------------------
    # 3) delete_save remove só o slot certo
    # ------------------------------------------------------------------
    print("\n[3] delete_save: remove só o slot alvo; inexistente não crasha")
    assert save_mgr.delete_save(2) is True
    assert save_mgr.save_metadata(2) is None
    assert not os.path.isfile(os.path.join(save_dir, "save_slot_2.json"))
    # Os outros permanecem intactos
    assert save_mgr.save_metadata(1)["pilot_name"] == "Ana"
    assert save_mgr.save_metadata(3)["pilot_name"] == "Carla"
    # Deletar de novo / slot que nunca existiu: False, sem exceção
    assert save_mgr.delete_save(2) is False
    assert save_mgr.delete_save(77) is False
    print("  ✓ slot 2 removido; 1 e 3 intactos; delete inexistente = False")

    # ------------------------------------------------------------------
    # 4) Compatibilidade retro: save v1 (sem pilot/saved_at/progression)
    # ------------------------------------------------------------------
    print("\n[4] Save 'antigo' (v1) ainda carrega e lista")
    bus._listeners.clear()
    universe, mission_mgr, faction_mgr, station_mgr = _fresh_managers(
        factions_data, templates)
    _, old_player = _make_player(universe, [50.0, 60.0], 4500)
    legacy = {
        "version": 1,
        "player_ship": old_player.to_save_dict(),
        "pips": {"weapons": 2, "shields": 2, "engines": 2},
        "credits": 4500,
        "missions": mission_mgr.get_save_data(),
        "factions": faction_mgr.get_save_data(),
        "last_docked_station_id": None,
        "camera_offset": [0.0, 0.0],
        # sem "pilot", sem "saved_at", sem "progression", sem "exploration"
    }
    save_mgr.save_game(2, legacy)

    meta = save_mgr.save_metadata(2)
    assert meta is not None
    assert meta["version"] == 1
    assert meta["pilot_name"] == "Piloto", meta          # default
    assert meta["credits"] == 4500
    assert meta["saved_at"] is None                       # v1 não tinha
    assert meta["progress"]["bounties_completed"] == 0    # default

    bus._listeners.clear()
    universe2, mission_mgr2, faction_mgr2, station_mgr2 = _fresh_managers(
        factions_data, templates)
    boot_pid, boot_player = _make_player(universe2, [0.0, 0.0], 0)
    player_mgr2 = PlayerManager(boot_player)
    energy_mgr2 = EnergyManager(boot_player)
    new_pid = apply_save_payload(
        payload=save_mgr.load_game(2), universe=universe2,
        player_mgr=player_mgr2, energy_mgr=energy_mgr2,
        mission_mgr=mission_mgr2, faction_mgr=faction_mgr2,
        station_mgr=station_mgr2, old_player_id=boot_pid,
    )
    assert universe2.entities[new_pid].credits == 4500
    print("  ✓ metadata com defaults (Piloto/0 caçadas/sem data); load OK")

    print("\nTeste de save multi-slot: OK")


if __name__ == "__main__":
    main()
