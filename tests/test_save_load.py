"""
Teste de save/load completo (headless, sem pygame).

Critério de aceitação do Ciclo C:
  "Salvo o jogo, fecho, reabro, e estou exatamente onde parei: mesma nave
   (modelo, HP, escudo, posição, rotação), mesmos créditos, mesmas missões
   ativas/concluídas e a mesma reputação de facção."

O teste:
  1. Constrói um estado de jogo "vivo" (managers instanciados diretamente).
  2. Monta o payload de save e grava com o SaveManager em diretório temporário.
  3. Cria managers NOVOS (estado zerado), carrega o save e aplica.
  4. Verifica campo a campo que o estado reconstruído bate com o original.
"""
import os
import sys
import json
import math
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
from systems.game_state_serializer import (
    build_save_payload, apply_save_payload, SAVE_VERSION,
)
from entities.ship import Ship
from entities.station import Station

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def _load_json(*parts):
    with open(os.path.join(ROOT, *parts), "r", encoding="utf-8") as f:
        return json.load(f)


def _make_player(universe, pos, rot):
    template = Ship(
        id="player",
        name="Wasp",
        ship_class="Small",
        model_id="wasp_combat",
        mass=100, energy_capacity=90, heat_dissipation=5,
        max_hp=70, current_hp=70,
        max_shields=80, current_shields=80,
        is_player=True,
        faction="United Humans",
        credits=50000,
        hardpoints={"weapon_small": 4, "weapon_medium": 1},
    )
    pid = universe.spawn_ship(template, pos)
    player = universe.entities[pid]
    player.rotation = rot
    return pid, player


def main():
    print("=" * 60)
    print("Teste de Save/Load completo")
    print("=" * 60)

    # O bus é global; isolamos limpando os listeners no início.
    bus._listeners.clear()

    factions_data = _load_json("data", "factions.json")["factions"]
    mission_templates = [
        t for t in _load_json("data", "mission_templates.json")["templates"]
        if t["type"] == "BOUNTY"
    ]

    # ----------------------------------------------------------------
    # 1) Construir um estado de jogo "vivo" e não-trivial.
    # ----------------------------------------------------------------
    universe = UniverseManager()
    player_mgr = None  # criado após spawn
    energy_mgr = None
    mission_mgr = MissionManager()
    faction_mgr = FactionManager()
    station_mgr = StationManager(universe)

    faction_mgr.setup_factions(factions_data)
    mission_mgr.set_templates(mission_templates)

    # Estação para registrar last_docked_station_id
    hub = Station(
        id="hub_alpha", name="Hub Alpha", position=[400, 400],
        faction="United Humans", services=["shipyard"],
        ship_inventory=["wasp_combat"], docking_radius=180,
    )
    station_mgr.spawn_station(hub)

    # Player com estado físico não-trivial
    pos = [1234.5, -678.25]
    rot = 137.5
    pid, player = _make_player(universe, list(pos), rot)
    player.velocity = [42.0, -17.5]

    player_mgr = PlayerManager(player)
    energy_mgr = EnergyManager(player)

    # Dano parcial (HP e escudo não cheios) + calor acumulado
    player.current_hp = 41.0
    player.current_shields = 23.5
    player.current_heat = 18.0
    player.credits = 73250

    # Pips alterados (afastados do padrão 2/2/2)
    player_mgr.pips = {"weapons": 4, "shields": 1, "engines": 1}
    player.pips = dict(player_mgr.pips)

    # Missões: 1 ativa, 1 concluída
    m_active = mission_mgr.generate_mission(faction="Pirates", difficulty=1.0)
    mission_mgr.accept_mission(m_active.id)
    m_active.kill_progress = 1  # progresso parcial

    m_done = mission_mgr.generate_mission(faction="United Humans", difficulty=1.0)
    mission_mgr.accept_mission(m_done.id)
    mission_mgr.complete_mission(m_done.id)

    active_ids = sorted(mission_mgr.active_missions.keys())
    completed_ids = sorted(mission_mgr.completed_missions)

    # Reputação alterada numa facção (eixo trust de Pirates)
    bus.emit("UPDATE_REPUTATION", {"faction": "Pirates", "impact": {"trust": -15}})
    pirate_trust = faction_mgr.reputation_axes["Pirates"]["trust"]

    # last_docked
    station_mgr.last_docked_station_id = "hub_alpha"

    print("\nEstado ORIGINAL:")
    print(f"  Nave: {player.name} ({player.model_id})")
    print(f"  HP {player.current_hp} | Escudo {player.current_shields} "
          f"| Calor {player.current_heat}")
    print(f"  Pos {player.position} | Rot {player.rotation}")
    print(f"  Créditos {player.credits} | Pips {player_mgr.pips}")
    print(f"  Missões ativas {active_ids} | concluídas {completed_ids}")
    print(f"  Reputação Pirates/trust: {pirate_trust}")

    # ----------------------------------------------------------------
    # 2) Montar payload e gravar com o SaveManager em dir temporário.
    # ----------------------------------------------------------------
    payload = build_save_payload(
        player_ship=player,
        pips=player_mgr.pips,
        mission_mgr=mission_mgr,
        faction_mgr=faction_mgr,
        last_docked_station_id=station_mgr.last_docked_station_id,
        camera_offset=[100.0, 200.0],
    )
    assert payload["version"] == SAVE_VERSION
    # Fonte única de créditos: top-level presente, NÃO duplicado na nave.
    assert payload["credits"] == 73250
    assert "credits" not in payload["player_ship"], \
        "créditos não devem ser duplicados dentro de player_ship"

    save_dir = tempfile.mkdtemp(prefix="space_rpg_save_")
    save_mgr = SaveManager(save_dir=save_dir)
    save_mgr.save_game(1, payload)
    save_path = os.path.join(save_dir, "save_slot_1.json")
    assert os.path.exists(save_path), "arquivo de save não foi criado"
    print(f"\n  ✓ Save gravado em {save_path}")

    # ----------------------------------------------------------------
    # 3) Managers NOVOS (estado zerado), carregar e aplicar.
    # ----------------------------------------------------------------
    bus._listeners.clear()  # simula um "novo jogo" sem listeners antigos

    universe2 = UniverseManager()
    mission_mgr2 = MissionManager()
    faction_mgr2 = FactionManager()
    station_mgr2 = StationManager(universe2)
    faction_mgr2.setup_factions(factions_data)
    mission_mgr2.set_templates(mission_templates)

    # Player "placeholder" zerado (como num boot de jogo) + seus managers
    boot_pid, boot_player = _make_player(universe2, [0.0, 0.0], 0.0)
    player_mgr2 = PlayerManager(boot_player)
    energy_mgr2 = EnergyManager(boot_player)

    loaded = save_mgr.load_game(1)
    assert loaded["version"] == SAVE_VERSION

    new_pid = apply_save_payload(
        payload=loaded,
        universe=universe2,
        player_mgr=player_mgr2,
        energy_mgr=energy_mgr2,
        mission_mgr=mission_mgr2,
        faction_mgr=faction_mgr2,
        station_mgr=station_mgr2,
        old_player_id=boot_pid,
    )
    rp = universe2.entities[new_pid]  # reconstructed player
    print(f"  ✓ Save carregado e aplicado (novo id: {new_pid})")

    # ----------------------------------------------------------------
    # 4) Asserts campo a campo.
    # ----------------------------------------------------------------
    EPS = 1e-6
    assert rp.model_id == "wasp_combat", rp.model_id
    assert rp.name == "Wasp", rp.name
    assert rp.ship_class == "Small"
    assert rp.faction == "United Humans"
    assert rp.is_player is True

    assert abs(rp.current_hp - 41.0) < EPS, rp.current_hp
    assert abs(rp.max_hp - 70.0) < EPS
    assert abs(rp.current_shields - 23.5) < EPS, rp.current_shields
    assert abs(rp.max_shields - 80.0) < EPS
    assert abs(rp.current_heat - 18.0) < EPS, rp.current_heat

    assert abs(rp.position[0] - pos[0]) < 1e-4, rp.position
    assert abs(rp.position[1] - pos[1]) < 1e-4, rp.position
    assert abs(rp.velocity[0] - 42.0) < 1e-4, rp.velocity
    assert abs(rp.velocity[1] - (-17.5)) < 1e-4, rp.velocity
    assert abs(rp.rotation - rot) < 1e-4, rp.rotation

    # Créditos (fonte única)
    assert rp.credits == 73250, rp.credits

    # Managers reapontados para a nave reconstruída
    assert player_mgr2.ship is rp, "player_mgr não reaponta para a nova nave"
    assert energy_mgr2.ship is rp, "energy_mgr não reaponta para a nova nave"

    # Pips restaurados em todos os lugares
    assert player_mgr2.pips == {"weapons": 4, "shields": 1, "engines": 1}, player_mgr2.pips
    assert rp.pips == {"weapons": 4, "shields": 1, "engines": 1}, rp.pips

    # Missões: mesmos IDs ativos e concluídos
    assert sorted(mission_mgr2.active_missions.keys()) == active_ids, \
        (sorted(mission_mgr2.active_missions.keys()), active_ids)
    assert sorted(mission_mgr2.completed_missions) == completed_ids, \
        (sorted(mission_mgr2.completed_missions), completed_ids)
    # Progresso parcial da missão ativa preservado
    restored_active = mission_mgr2.active_missions[active_ids[0]]
    assert restored_active.kill_progress == 1, restored_active.kill_progress

    # Reputação: eixo alterado preservado
    assert faction_mgr2.reputation_axes["Pirates"]["trust"] == pirate_trust, \
        faction_mgr2.reputation_axes["Pirates"]["trust"]

    # last_docked restaurado
    assert station_mgr2.last_docked_station_id == "hub_alpha", \
        station_mgr2.last_docked_station_id

    print("\nEstado RECONSTRUÍDO confere com o original:")
    print(f"  Nave: {rp.name} ({rp.model_id}) | HP {rp.current_hp} "
          f"| Escudo {rp.current_shields} | Calor {rp.current_heat}")
    print(f"  Pos {rp.position} | Rot {rp.rotation} | Vel {rp.velocity}")
    print(f"  Créditos {rp.credits} | Pips {rp.pips}")
    print(f"  Missões ativas {sorted(mission_mgr2.active_missions.keys())} "
          f"| concluídas {sorted(mission_mgr2.completed_missions)}")
    print(f"  Reputação Pirates/trust: "
          f"{faction_mgr2.reputation_axes['Pirates']['trust']}")
    print(f"  last_docked: {station_mgr2.last_docked_station_id}")

    print("\nTeste de save/load: OK")


if __name__ == "__main__":
    main()
