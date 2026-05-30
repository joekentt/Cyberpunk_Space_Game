import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.data_loader import DataLoader
from systems.mission_manager import MissionManager
from systems.economy_manager import EconomyManager
from core.event_bus import bus
import json

def test_mission_system():
    print("--- Iniciando Teste do Sistema de Missões (Fase 6) ---")
    
    # 1. Setup
    loader = DataLoader(data_dir="data")
    mission_mgr = MissionManager()
    econ_mgr = EconomyManager(initial_credits=1000)
    
    # Carregar templates
    templates = loader.load_json("mission_templates.json")["templates"]
    mission_mgr.set_templates(templates)
    
    # 2. Configurar Eventos
    def on_mission_accepted(data):
        print(f"✅ Missão Aceita: {data['title']} | Recompensa: {data['reward_credits']}cr")
    
    def on_mission_completed(data):
        print(f"🏆 Missão Concluída: {data['title']}!")
        print(f"   Impacto Reputacional: {data['reputation_impact']}")

    def on_credits_changed(amount):
        print(f"💰 Saldo Atual: {amount}cr")

    bus.subscribe("MISSION_ACCEPTED", on_mission_accepted)
    bus.subscribe("MISSION_COMPLETED", on_mission_completed)
    bus.subscribe("ADD_CREDITS", econ_mgr.add_credits)
    bus.subscribe("CREDITS_CHANGED", on_credits_changed)

    # 3. Gerar e Aceitar Missão
    print("\nGerando missões para a facção 'United Humans'...")
    m1 = mission_mgr.generate_mission(faction="United Humans")
    m2 = mission_mgr.generate_mission(faction="United Humans")
    
    print(f"Missões disponíveis: {len(mission_mgr.available_missions)}")
    
    mission_id = m1.id
    mission_mgr.accept_mission(mission_id)
    
    # 4. Simular Conclusão de Missão
    print(f"\nSimulando conclusão da missão {mission_id}...")
    # Usamos o evento de debug para simplificar o teste
    mission_mgr.update_progress("DEBUG_COMPLETE_MISSION", mission_id)
    
    # 5. Validar Persistência
    print("\nTestando serialização de missões...")
    save_data = mission_mgr.get_save_data()
    print(f"Dados de Save (Missões Completadas): {save_data['completed']}")
    
    # 6. Testar Load
    new_mgr = MissionManager()
    new_mgr.load_save_data(save_data)
    print(f"Novo Manager carregado com {len(new_mgr.completed_missions)} missões concluídas.")

    print("\n--- Teste Concluído com Sucesso ---")

if __name__ == "__main__":
    test_mission_system()
