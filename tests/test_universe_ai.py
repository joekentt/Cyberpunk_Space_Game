import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.data_loader import DataLoader
from entities.ship import Ship
from systems.universe_manager import UniverseManager
from systems.npc_manager import NPCManager
from core.event_bus import bus
import time

def test_universe_ai():
    print("--- Iniciando Teste de Universo e IA (Fase 4) ---")
    
    # 1. Setup do Universo
    universe = UniverseManager()
    loader = DataLoader(data_dir="data")
    
    # Carregar templates
    ship_templates = loader.load_json("ships.json")["ships"]
    scout_template = Ship.from_dict(ship_templates[0]) # Void Runner
    freighter_template = Ship.from_dict(ship_templates[1]) # Iron Whale
    
    # 2. Spawn de Entidades
    print("\nSpawning: Jogador (Freighter) e NPC (Scout)...")
    player_id = universe.spawn_ship(freighter_template, position=[0, 0])
    npc_id = universe.spawn_ship(scout_template, position=[500, 500])
    
    player_ship = universe.entities[player_id]
    npc_ship = universe.entities[npc_id]
    
    # 3. Inicializar IA para o NPC
    npc_ai = NPCManager(npc_ship, target=player_ship)
    
    # 4. Simulação de 5 segundos
    dt = 1/60.0
    print(f"\nSimulando: NPC perseguindo o Jogador...")
    
    for i in range(300): # 5 segundos
        # Atualiza IA
        npc_ai.update(dt)
        
        # Atualiza Universo (Física)
        universe.update(dt)
        
        if i % 60 == 0:
            dx = player_ship.position[0] - npc_ship.position[0]
            dy = player_ship.position[1] - npc_ship.position[1]
            dist = (dx**2 + dy**2)**0.5
            print(f"T={i*dt:.1f}s | Estado IA: {npc_ai.state} | Distância: {dist:.2f} | Pos NPC: [{npc_ship.position[0]:.1f}, {npc_ship.position[1]:.1f}]")

    # 5. Teste de Fuga (FLEE)
    print("\nSimulando: NPC com escudos baixos (FLEE)...")
    npc_ship.current_shields = 10.0 # Abaixo do threshold de 20.0
    
    for i in range(300, 480): # Mais 3 segundos
        npc_ai.update(dt)
        universe.update(dt)
        
        if i % 60 == 0:
            dx = player_ship.position[0] - npc_ship.position[0]
            dy = player_ship.position[1] - npc_ship.position[1]
            dist = (dx**2 + dy**2)**0.5
            print(f"T={i*dt:.1f}s | Estado IA: {npc_ai.state} | Distância: {dist:.2f} | Vel NPC: {npc_ship.velocity[0]:.2f}")

    print("\n--- Teste Concluído com Sucesso ---")

if __name__ == "__main__":
    test_universe_ai()
