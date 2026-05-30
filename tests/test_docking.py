"""
Teste de docking e mercado de naves (headless).
"""
import os
import sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.event_bus import bus
from systems.universe_manager import UniverseManager
from systems.station_manager import StationManager
from entities.ship import Ship
from entities.station import Station


def main():
    print("=" * 60)
    print("Teste de Docking + Mercado")
    print("=" * 60)

    universe = UniverseManager()
    station_mgr = StationManager(universe)

    # Player
    player_template = Ship(
        id="player",
        name="Skiff Mk I",
        ship_class="Small",
        model_id="starter_skiff",
        mass=120, energy_capacity=100, heat_dissipation=8,
        max_hp=80, current_hp=80,
        max_shields=100, current_shields=100,
        is_player=True,
        faction="United Humans",
        credits=50000,
    )
    pid = universe.spawn_ship(player_template, [400, 400])
    player = universe.entities[pid]

    # Estação
    hub = Station(
        id="hub_a",
        name="Hub Alpha",
        position=[1000, 400],
        faction="United Humans",
        services=["shipyard", "repair"],
        ship_inventory=["wasp_combat", "albatross_explorer"],
        docking_radius=180,
    )
    station_mgr.spawn_station(hub)

    # Log de eventos
    events = []
    bus.subscribe("DOCKING_ENTER_RANGE", lambda d: events.append(("ENTER", d)))
    bus.subscribe("DOCKING_EXIT_RANGE", lambda d: events.append(("EXIT", d)))
    bus.subscribe("DOCKED", lambda d: events.append(("DOCKED", d)))
    bus.subscribe("UNDOCKED", lambda d: events.append(("UNDOCKED", d)))
    bus.subscribe("SHIP_PURCHASED", lambda d: events.append(("BOUGHT", d)))

    print(f"\nEstado inicial:")
    print(f"  Player @ {player.position}, créditos {player.credits}")
    print(f"  Estação @ {hub.position}, raio docking {hub.docking_radius}")
    print(f"  Distância inicial: {hub.distance_to(player.position):.0f}px (FORA do raio)")

    # 1) Update inicial - fora do raio
    station_mgr.update(0.016, player.position)
    assert station_mgr.docking_state == "free", f"Esperado free, foi {station_mgr.docking_state}"
    print(f"  ✓ Estado 'free' (fora do raio)")

    # 2) Mover player pra dentro do raio
    player.position = [880, 400]   # 120px da estação, dentro do raio
    station_mgr.update(0.016, player.position)
    assert station_mgr.docking_state == "approach", f"Esperado approach, foi {station_mgr.docking_state}"
    print(f"  ✓ Estado 'approach' (dentro do raio)")

    # 3) Tentar acoplar
    ok = station_mgr.request_dock()
    assert ok, "request_dock retornou False"
    assert station_mgr.docking_state == "docked"
    print(f"  ✓ Acoplado em '{station_mgr.stations[station_mgr.current_station_id].name}'")

    # 4) Simular compra (carrega catálogo direto, sem UI)
    import json
    ships_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                              "data", "ships.json")
    with open(ships_path) as f:
        ships_catalog = json.load(f)["ships"]
    wasp_data = next(s for s in ships_catalog if s["id"] == "wasp_combat")
    price = wasp_data["base_price"]

    credits_before = player.credits
    player.credits -= price
    bus.emit("SHIP_PURCHASED", {"ship_data": wasp_data, "buyer_id": player.id})
    print(f"  ✓ Comprou {wasp_data['name']} por {price:,} cr".replace(",", "."))
    print(f"    Créditos: {credits_before} → {player.credits}")
    assert any(e[0] == "BOUGHT" for e in events), "Evento SHIP_PURCHASED não emitido"

    # 5) Desacoplar
    station_mgr.undock()
    assert station_mgr.docking_state in ("approach", "free")
    print(f"  ✓ Desacoplado (estado: {station_mgr.docking_state})")

    # 6) Mover pra longe e ver "EXIT"
    player.position = [400, 400]
    station_mgr.update(0.016, player.position)
    assert station_mgr.docking_state == "free"
    print(f"  ✓ Saiu do raio (estado: 'free')")

    # 7) Verificar last_docked_station_id pra respawn
    assert station_mgr.last_docked_station_id == "hub_a"
    print(f"  ✓ last_docked_station registrado: '{station_mgr.last_docked_station_id}'")

    respawn_station = station_mgr.get_respawn_station()
    assert respawn_station is not None
    print(f"  ✓ Estação de respawn: '{respawn_station.name}'")

    print()
    print(f"Eventos capturados ({len(events)}):")
    for e_name, _ in events:
        print(f"  - {e_name}")

    print("\nTeste de docking + mercado: OK")


if __name__ == "__main__":
    main()
