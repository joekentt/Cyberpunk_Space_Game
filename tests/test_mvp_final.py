import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from main import SpaceRPGApp
import threading
import time

def test_mvp_final():
    print("--- Iniciando Teste Final do MVP Integrado ---")
    app = SpaceRPGApp()
    
    # Rodar o jogo em uma thread separada para podermos parar
    game_thread = threading.Thread(target=app.start_new_game)
    game_thread.daemon = True
    game_thread.start()
    
    print("Jogo rodando por 5 segundos para validar integração...")
    time.sleep(5)
    
    print("\nValidando estado final...")
    if app.player_mgr and app.universe.entities:
        print("✅ Jogador inicializado corretamente.")
    if app.npc_ais:
        print(f"✅ {len(app.npc_ais)} NPC(s) inicializado(s) com IA ativa.")
    
    app.loop.stop()
    print("--- Teste Final Concluído ---")

if __name__ == "__main__":
    test_mvp_final()
