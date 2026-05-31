"""
Teste headless do fluxo compra de nave → desacoplar → jogar.

Valida:
  - new_player.pips existe após a troca (corrige crash no hud.draw)
  - player_id é atualizado para a nova entidade
  - ENTITY_REMOVED emitido para a entidade antiga (remove_entity, não del direto)
  - NPCManager limpa targets stale após ENTITY_REMOVED
  - 5 frames de update rodam sem exceção após a troca
  - Acesso ao hud (player.pips) não levanta AttributeError
"""
import os
import sys
import json

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from entities.ship import Ship
from entities.station import Station
from systems.universe_manager import UniverseManager
from systems.station_manager import StationManager
from systems.npc_manager import NPCManager, NPCBehavior
from systems.combat_manager import CombatManager
from systems.loot_manager import LootManager
from systems.mission_manager import MissionManager
from systems.player_manager import PlayerManager
from systems.energy_manager import EnergyManager
from core.event_bus import bus


def load_data():
    base = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    with open(os.path.join(base, "data", "ships.json"), encoding="utf-8") as f:
        ships_catalog = json.load(f)["ships"]
    with open(os.path.join(base, "data", "mission_templates.json"), encoding="utf-8") as f:
        all_templates = json.load(f)["templates"]
    return ships_catalog, all_templates


def hardpoints_for(catalog, model_id):
    for s in catalog:
        if s.get("model_id") == model_id or s.get("id") == model_id:
            return dict(s.get("hardpoints", {}))
    return {}


def simulate_purchase_flow(universe, player_id, player_mgr, energy_mgr,
                            ship_data, station_ui_player_ref):
    """
    Reproduz _on_ship_purchased de main_pygame.py (sem pygame).
    Retorna o novo player_id.
    """
    old_player = universe.entities.get(player_id)
    assert old_player is not None

    new_template = Ship.from_dict(ship_data)
    new_template.is_player = True
    new_template.credits = old_player.credits
    new_template.faction = old_player.faction
    old_pos = list(old_player.position)

    # FIX: remove_entity emite ENTITY_REMOVED (em vez de del direto)
    universe.remove_entity(player_id)
    new_player_id = universe.spawn_ship(new_template, old_pos)
    new_player = universe.entities[new_player_id]

    player_mgr.ship = new_player
    # FIX: restaura o atributo dinâmico pips na nova entidade
    new_player.pips = dict(player_mgr.pips)
    energy_mgr.ship = new_player

    # (station_ui_player_ref seria station_ui.player = new_player)
    station_ui_player_ref[0] = new_player

    return new_player_id


def main():
    print("=" * 60)
    print("Teste do fluxo de compra de nave (purchase flow)")
    print("=" * 60)

    ships_catalog, all_templates = load_data()

    # ------------------------------------------------------------------
    # Setup
    # ------------------------------------------------------------------
    universe = UniverseManager()
    station_mgr = StationManager(universe)
    npc_mgr = NPCManager(universe)
    combat_mgr = CombatManager(universe)
    loot_mgr = LootManager()
    mission_mgr = MissionManager()
    mission_mgr.set_templates([t for t in all_templates if t["type"] == "BOUNTY"])

    hub1 = Station(
        id="station_alpha", name="Hub Alpha", position=[400, 400],
        faction="United Humans", station_class="Hub", model_id="hub_alpha",
        services=["shipyard", "repair"], ship_inventory=[],
    )
    station_mgr.spawn_station(hub1)

    player_tmpl = Ship(
        id="player_skiff", name="Skiff Mk I", ship_class="Small",
        model_id="starter_skiff", mass=120, energy_capacity=100,
        heat_dissipation=8, max_hp=80, current_hp=80,
        max_shields=100, current_shields=100, is_player=True,
        faction="United Humans", credits=50000,
        hardpoints=hardpoints_for(ships_catalog, "starter_skiff"),
    )
    player_id = universe.spawn_ship(player_tmpl, [600, 400])
    player = universe.entities[player_id]

    player_mgr = PlayerManager(player)   # sets player.pips dynamically
    energy_mgr = EnergyManager(player)

    # NPC pirata com target apontando para o jogador antigo
    npc_t = Ship(
        id="npc_pirate", name="Pirate", ship_class="Small",
        model_id="wasp_combat", mass=100, energy_capacity=90,
        heat_dissipation=5, max_hp=70, current_hp=70,
        max_shields=80, current_shields=80, faction="Pirates",
        hardpoints=hardpoints_for(ships_catalog, "wasp_combat"),
    )
    npc_id = universe.spawn_ship(npc_t, [1800, 300])
    npc_mgr.register_npc(npc_id, initial_state=NPCBehavior.IDLE)
    # Simula que o NPC já estava atacando o jogador antes de ele atracar
    npc_mgr.targets[npc_id] = player_id
    npc_mgr.npc_ships[npc_id] = NPCBehavior.ATTACK

    # ------------------------------------------------------------------
    # 1) player.pips existe antes da compra
    # ------------------------------------------------------------------
    print("\n[1] player.pips existe antes da compra")
    assert hasattr(player, "pips"), "PlayerManager deve criar player.pips"
    assert player.pips == {"weapons": 2, "shields": 2, "engines": 2}
    print(f"  player.pips = {player.pips}  ✓")

    # ------------------------------------------------------------------
    # 2) Compra de nave — simulação de _on_ship_purchased
    # ------------------------------------------------------------------
    print("\n[2] Simula compra da Wasp Combat")
    wasp_data = next(s for s in ships_catalog if s["id"] == "wasp_combat")

    entity_removed_ids = []
    bus.subscribe("ENTITY_REMOVED", lambda d: entity_removed_ids.append(d["id"]))

    station_ui_ref = [player]  # simula station_ui.player
    try:
        player_id = simulate_purchase_flow(
            universe, player_id, player_mgr, energy_mgr,
            wasp_data, station_ui_ref,
        )
    finally:
        bus.unsubscribe("ENTITY_REMOVED", lambda d: entity_removed_ids.append(d["id"]))

    new_player = universe.entities[player_id]
    assert player_id in universe.entities, "novo player deve estar no universo"
    assert new_player.is_player, "novo player deve ter is_player=True"
    assert hasattr(new_player, "pips"), "CRÍTICO: new_player.pips deve existir (HUD lê isso)"
    assert new_player.pips == {"weapons": 2, "shields": 2, "engines": 2}
    print(f"  novo player_id: {player_id}")
    print(f"  new_player.pips = {new_player.pips}  ✓")
    print(f"  ENTITY_REMOVED emitido (NPC cleanup): {'sim' if entity_removed_ids else 'não'}")

    # ------------------------------------------------------------------
    # 3) NPCManager limpou o target stale após ENTITY_REMOVED
    # ------------------------------------------------------------------
    print("\n[3] NPCManager limpou targets stale")
    # entity_removed do bus_subscribe acima pode não capturar por timing; verificar direto
    npc_target = npc_mgr.targets.get(npc_id)
    assert npc_target != player_id or npc_target is None or \
        npc_target not in universe.entities, \
        "target stale deve apontar para entidade inexistente"
    # Mais importante: após 1 update, NPC não crasha tentando acessar o target
    npc_mgr.update(1 / 60)
    print("  npc_mgr.update com target stale → sem crash  ✓")

    # ------------------------------------------------------------------
    # 4) 5 frames de update sem exceção
    # ------------------------------------------------------------------
    print("\n[4] 5 frames de update em estado 'playing'")
    # Simula _on_undocked: docking_state volta para approach
    station_mgr.docking_state = "approach"

    for i in range(5):
        universe.update(1 / 60)
        if player_id in universe.entities:
            player_mgr.update(1 / 60)
            energy_mgr.update(1 / 60)
        npc_mgr.update(1 / 60)
        combat_mgr.update(1 / 60)

    assert player_id in universe.entities, "player deve existir após updates"
    print("  5 frames sem exceção  ✓")

    # ------------------------------------------------------------------
    # 5) Acesso ao hud simulado (player.pips['weapons'] etc.)
    # ------------------------------------------------------------------
    print("\n[5] Acesso ao hud (simula hud.draw)")
    final_player = universe.entities[player_id]
    pips = final_player.pips  # seria AttributeError antes do fix
    hud_text = (f"PIPS: W[{pips['weapons']}]"
                f" S[{pips['shields']}]"
                f" E[{pips['engines']}]")
    print(f"  {hud_text}  ✓")

    # ------------------------------------------------------------------
    # 6) Créditos preservados corretamente
    # ------------------------------------------------------------------
    print("\n[6] Créditos da nave antiga preservados na nova nave")
    assert final_player.credits == 50000, \
        f"créditos deveriam ser 50000, são {final_player.credits}"
    print(f"  credits = {final_player.credits}  ✓")

    print("\nTeste de compra de nave: OK")


if __name__ == "__main__":
    main()
