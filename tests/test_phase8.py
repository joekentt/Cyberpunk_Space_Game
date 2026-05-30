import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import time
from core.event_bus import bus
from core.data_loader import DataLoader
from systems.universe_manager import UniverseManager
from systems.npc_manager import NPCManager, NPCBehavior
from systems.faction_manager import FactionManager
from systems.event_manager import EventManager
from entities.ship import Ship

def test_phase8():
    print("--- Iniciando Teste da Fase 8: IA, Wingmen e Eventos ---")
    
    # 1. Setup
    loader = DataLoader(data_dir="data")
    universe = UniverseManager()
    faction_mgr = FactionManager()
    npc_mgr = NPCManager(universe)
    event_mgr = EventManager(universe, faction_mgr)
    
    # Carregar dados
    factions_data = loader.load_json("factions.json")["factions"]
    faction_mgr.setup_factions(factions_data)
    
    ship_data = loader.load_json("ships.json")["ships"][0]
    ship_template = Ship.from_dict(ship_data)
    
    # 2. Spawn Jogador e NPCs
    player_id = universe.spawn_ship(ship_template, [0, 0])
    player_ship = universe.entities[player_id]
    player_ship.is_player = True # Flag para o NPCManager encontrar o jogador
    
    npc1_id = universe.spawn_ship(ship_template, [200, 200])
    npc_mgr.register_npc(npc1_id, initial_state=NPCBehavior.CHASE)
    
    npc2_id = universe.spawn_ship(ship_template, [-200, -200])
    npc_mgr.register_npc(npc2_id, initial_state=NPCBehavior.IDLE)
    
    print(f"NPC 1 registrado como CHASE. NPC 2 registrado como IDLE.")
    
    # 3. Testar Recrutamento de Wingman
    print("\nRecrutando NPC 2 como Wingman...")
    bus.emit("RECRUIT_WINGMAN", npc2_id)
    
    # 4. Simular Loop
    print("\nSimulando 2 segundos de universo...")
    dt = 0.1
    for _ in range(20):
        universe.update(dt)
        npc_mgr.update(dt)
        event_mgr.update(dt)
        time.sleep(0.01)
        
    print(f"Posição Jogador: {player_ship.position}")
    print(f"Posição Wingman (NPC 2): {universe.entities[npc2_id].position}")
    print(f"Estado NPC 1: {npc_mgr.npc_ships[npc1_id]}")
    
    # 5. Testar Evento Dinâmico Manual
    print("\nDisparando evento dinâmico manual...")
    event_mgr.trigger_random_event()
    
    print("\n--- Teste da Fase 8 Concluído ---")

if __name__ == "__main__":
    test_phase8()
