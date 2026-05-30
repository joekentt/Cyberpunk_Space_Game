import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.data_loader import DataLoader
from systems.faction_manager import FactionManager
from systems.mission_manager import MissionManager
from core.event_bus import bus

def test_faction_system():
    print("--- Iniciando Teste de Facções e Reputação (Fase 7) ---")
    
    # 1. Setup
    loader = DataLoader(data_dir="data")
    faction_mgr = FactionManager()
    mission_mgr = MissionManager()
    
    # Carregar dados
    factions_data = loader.load_json("factions.json")["factions"]
    faction_mgr.setup_factions(factions_data)
    
    mission_templates = loader.load_json("mission_templates.json")["templates"]
    mission_mgr.set_templates(mission_templates)
    
    # 2. Verificar Estado Inicial
    print(f"\nReputação Inicial com United Humans: {faction_mgr.player_reputation['United Humans']} ({faction_mgr.get_reputation_level('United Humans')})")
    print(f"Reputação Inicial com Pirates: {faction_mgr.player_reputation['Pirates']} ({faction_mgr.get_reputation_level('Pirates')})")

    # 3. Simular Missão Concluída (Impacto na Reputação)
    print("\nGerando e concluindo missão para United Humans...")
    mission = mission_mgr.generate_mission(faction="United Humans")
    mission_mgr.accept_mission(mission.id)
    
    # A conclusão da missão emite UPDATE_REPUTATION, que o FactionManager escuta
    mission_mgr.complete_mission(mission.id)
    
    # 4. Verificar Mudança
    print(f"\nNova Reputação com United Humans: {faction_mgr.player_reputation['United Humans']} ({faction_mgr.get_reputation_level('United Humans')})")
    print(f"Nova Reputação com Pirates: {faction_mgr.player_reputation['Pirates']} ({faction_mgr.get_reputation_level('Pirates')})")

    # 5. Testar Mudança de Nível
    print("\nAdicionando +100 de reputação com United Humans...")
    faction_mgr.add_reputation("United Humans", 100)
    print(f"Nível Final com United Humans: {faction_mgr.get_reputation_level('United Humans')}")

    # 6. Testar Persistência
    print("\nTestando serialização de facções...")
    save_data = faction_mgr.get_save_data()
    print(f"Dados de Save: {save_data['player_reputation']}")
    
    new_mgr = FactionManager()
    new_mgr.load_save_data(save_data)
    print(f"Novo Manager carregado. Reputação com United Humans: {new_mgr.player_reputation['United Humans']}")

    print("\n--- Teste Concluído com Sucesso ---")

if __name__ == "__main__":
    test_faction_system()
