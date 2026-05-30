import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.save_manager import SaveManager
from systems.loot_manager import LootManager
from systems.economy_manager import EconomyManager
from core.event_bus import bus
import os

def test_progression():
    print("--- Iniciando Teste de Persistência e Progressão (Fase 3) ---")
    
    # 1. Inicializar Managers
    save_sys = SaveManager(save_dir="saves")
    loot_sys = LootManager()
    econ_sys = EconomyManager(initial_credits=500)
    
    # 2. Configurar Eventos
    bus.subscribe("LOOT_GENERATED", econ_sys.on_loot_collected)
    
    def on_credits_changed(amount):
        print(f"💰 Créditos do Jogador: {amount}")
    bus.subscribe("CREDITS_CHANGED", on_credits_changed)

    # 3. Simular Gameplay: Destruição de naves e ganho de loot
    print("\nSimulando: Destruição de uma nave 'Medium'...")
    loot_sys.on_ship_destroyed({"class": "Medium"})
    
    print("Simulando: Destruição de uma nave 'Large'...")
    loot_sys.on_ship_destroyed({"class": "Large"})

    # 4. Simular Compra de Módulo
    print("\nSimulando: Compra de um módulo de 'Laser' por 1200 créditos...")
    laser_module = {"id": "laser_01", "name": "Pulse Laser", "price": 1200}
    success = econ_sys.buy_module(laser_module)
    print(f"Compra realizada: {'Sucesso' if success else 'Falha (Créditos Insuficientes)'}")

    # 5. Testar Persistência (Save/Load)
    print("\nSimulando: Salvando o estado do jogo...")
    game_state = {
        "player": {
            "credits": econ_sys.player_credits,
            "inventory": ["basic_module_scrap"]
        },
        "universe": {
            "current_system": "Alpha Centauri"
        }
    }
    save_sys.save_game(slot=1, data=game_state)

    print("\nSimulando: Carregando o estado do jogo...")
    loaded_data = save_sys.load_game(slot=1)
    print(f"Dados carregados: Créditos = {loaded_data['player']['credits']}, Sistema = {loaded_data['universe']['current_system']}")

    # Validação final
    assert loaded_data['player']['credits'] == econ_sys.player_credits
    print("\n--- Teste Concluído com Sucesso ---")

if __name__ == "__main__":
    test_progression()
