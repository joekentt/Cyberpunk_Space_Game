import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.data_loader import DataLoader
from systems.faction_manager import FactionManager
from systems.mission_manager import MissionManager
from systems.economy_manager import EconomyManager
from core.event_bus import bus

def test_reputation_v2():
    print("--- Iniciando Teste de Reputação Multi-Eixo (Prompt 7) ---")
    
    # 1. Setup
    loader = DataLoader(data_dir="data")
    faction_mgr = FactionManager()
    mission_mgr = MissionManager()
    econ_mgr = EconomyManager(initial_credits=5000)
    
    factions_data = loader.load_json("factions.json")["factions"]
    faction_mgr.setup_factions(factions_data)
    
    mission_templates = loader.load_json("mission_templates.json")["templates"]
    mission_mgr.set_templates(mission_templates)
    
    # 2. Verificar Eixos Iniciais
    print(f"\nEixos Iniciais (United Humans): {faction_mgr.reputation_axes['United Humans']}")
    
    # 3. Testar Impacto de Missão (Multi-Eixo)
    print("\nConcluindo missão de Comércio para United Humans...")
    # Forçamos uma missão de TRADE para testar Economic Value
    mission = mission_mgr.generate_mission(faction="United Humans")
    # Simulamos que a missão é do tipo TRADE alterando o tipo manualmente para o teste
    mission.type = "TRADE"
    mission.reputation_impact = {"trust": 5, "economic_value": 20}
    
    mission_mgr.accept_mission(mission.id)
    mission_mgr.complete_mission(mission.id)
    
    print(f"Novos Eixos (United Humans): {faction_mgr.reputation_axes['United Humans']}")
    
    # 4. Testar Efeito no Mercado
    base_price = 1000
    multiplier = faction_mgr.get_market_multiplier("United Humans")
    final_price = econ_mgr.get_adjusted_price(base_price, multiplier)
    print(f"\nPreço Base: {base_price} | Multiplicador: {multiplier:.2f} | Preço Final: {final_price}")
    
    # 5. Testar Permissão de Acoplagem (Docking)
    print(f"Pode acoplar em United Humans? {faction_mgr.can_dock('United Humans')}")
    
    print("\nSimulando alta agressividade (+60 aggression)...")
    faction_mgr.update_axis("United Humans", "aggression", 60)
    print(f"Pode acoplar agora? {faction_mgr.can_dock('United Humans')}")
    
    # 6. Testar Flags Históricas
    print("\nAdicionando Flag Histórica: 'HERO_OF_SOL'...")
    faction_mgr.add_historical_flag("HERO_OF_SOL")
    print(f"Flags Históricas Ativas: {faction_mgr.historical_flags}")
    
    # 7. Testar Decaimento (Simulado)
    print(f"\nAgressão antes do decaimento: {faction_mgr.reputation_axes['United Humans']['aggression']}")
    # Simulamos um tick longo para forçar decaimento
    for _ in range(100):
        faction_mgr.on_tick(100.0)
    print(f"Agressão após decaimento simulado: {faction_mgr.reputation_axes['United Humans']['aggression']}")

    print("\n--- Teste de Reputação V2 Concluído ---")

if __name__ == "__main__":
    test_reputation_v2()
