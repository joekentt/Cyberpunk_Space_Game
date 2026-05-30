import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import time
from core.event_bus import bus
from core.data_loader import DataLoader
from systems.universe_manager import UniverseManager
from systems.npc_manager import NPCManager
from systems.faction_manager import FactionManager
from systems.dialogue_manager import DialogueManager
from systems.ai_orchestrator import AIOrchestrator
from entities.ship import Ship

def test_final_integration():
    print("--- Iniciando Teste de Integração Final (Fase 10) ---")
    
    # 1. Setup de todos os sistemas
    loader = DataLoader(data_dir="data")
    universe = UniverseManager()
    faction_mgr = FactionManager()
    npc_mgr = NPCManager(universe)
    dialogue_mgr = DialogueManager()
    ai_orch = AIOrchestrator(universe, npc_mgr)
    
    # Inicializar dados
    factions_data = loader.load_json("factions.json")["factions"]
    faction_mgr.setup_factions(factions_data)
    
    ship_data = loader.load_json("ships.json")["ships"][0]
    ship_template = Ship.from_dict(ship_data)
    
    # 2. Registrar eventos de diálogo para visualização
    bus.subscribe("DIALOGUE_TRIGGERED", lambda d: print(f"[DIÁLOGO] {d['speaker']}: {d['text']}"))
    
    # 3. Spawn Jogador e Inimigos da mesma facção
    player_id = universe.spawn_ship(ship_template, [0, 0])
    universe.entities[player_id].is_player = True
    
    print("\nSpawning esquadrão de Piratas...")
    p1_id = universe.spawn_ship(ship_template, [100, 100])
    universe.entities[p1_id].faction = "Pirates"
    npc_mgr.register_npc(p1_id, initial_state="CHASE")
    
    p2_id = universe.spawn_ship(ship_template, [150, 150])
    universe.entities[p2_id].faction = "Pirates"
    npc_mgr.register_npc(p2_id, initial_state="IDLE")
    
    # 4. Simular destruição de um membro para testar AIOrchestrator (Vingança)
    print("\nSimulando destruição de Pirata 1 pelo Jogador...")
    bus.emit("SHIP_DESTROYED", {"ship_id": p1_id, "attacker_id": player_id})
    
    # 5. Simular Loop para ver reações
    print("\nSimulando 1 segundo de reações...")
    dt = 0.1
    for _ in range(10):
        universe.update(dt)
        npc_mgr.update(dt)
        time.sleep(0.01)

    print("\n--- Teste de Integração Final Concluído ---")

if __name__ == "__main__":
    test_final_integration()
