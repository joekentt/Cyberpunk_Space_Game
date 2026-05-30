import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.data_loader import DataLoader
from entities.ship import Ship
from systems.player_manager import PlayerManager
from systems.energy_manager import EnergyManager
from core.event_bus import bus
import time

def test_core_loop():
    print("--- Iniciando Teste do Core Loop (Fase 2) ---")
    
    # 1. Carregar dados da nave
    loader = DataLoader(data_dir="data")
    ship_data = loader.load_json("ships.json")["ships"][0] # Void Runner
    player_ship = Ship.from_dict(ship_data)
    print(f"Nave do Jogador: {player_ship.name} carregada.")

    # 2. Inicializar Managers
    player_sys = PlayerManager(player_ship)
    energy_sys = EnergyManager(player_ship)
    
    # 3. Listeners de Eventos para validação
    def on_heat_warning(heat):
        print(f"⚠️ ALERTA DE CALOR: {heat:.2f}%")
    bus.subscribe("HEAT_WARNING", on_heat_warning)

    # 4. Simulação de 5 segundos de gameplay
    dt = 1/60.0
    print("\nSimulando: Aceleração total por 2 segundos...")
    for i in range(120): # 2 segundos a 60 FPS
        player_sys.accelerate(dt)
        player_sys.update(dt)
        energy_sys.update(dt)
        
        if i % 30 == 0:
            print(f"T={i*dt:.1f}s | Pos: [{player_ship.position[0]:.2f}, {player_ship.position[1]:.2f}] | Vel: {player_ship.velocity[0]:.2f} | Calor: {player_ship.current_heat:.2f}")

    print("\nSimulando: Mudança de Pips para Escudos e espera de 3 segundos...")
    energy_sys.set_pips(weapons=0, shields=4, engines=2)
    player_ship.current_shields = 50.0 # Simula dano
    
    for i in range(120, 300): # Mais 3 segundos
        player_sys.update(dt)
        energy_sys.update(dt)
        
        if i % 60 == 0:
            print(f"T={i*dt:.1f}s | Vel: {player_ship.velocity[0]:.2f} (Inércia) | Escudos: {player_ship.current_shields:.2f}% | Calor: {player_ship.current_heat:.2f}")

    print("\n--- Teste Concluído com Sucesso ---")

if __name__ == "__main__":
    test_core_loop()
