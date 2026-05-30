import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.event_bus import bus
from core.game_loop import GameLoop
from core.data_loader import DataLoader
import time

# 1. Teste do DataLoader
print("--- Testando DataLoader ---")
loader = DataLoader(data_dir="data")
try:
    ship_data = loader.load_json("ships.json")
    print(f"Dados carregados com sucesso: {len(ship_data['ships'])} naves encontradas.")
    for ship in ship_data['ships']:
        print(f" - Nave: {ship['name']} ({ship['role']})")
except Exception as e:
    print(f"Erro no DataLoader: {e}")

# 2. Teste do EventBus
print("\n--- Testando EventBus ---")
def on_test_event(data):
    print(f"Evento recebido com dados: {data}")

bus.subscribe("TEST_EVENT", on_test_event)
bus.emit("TEST_EVENT", {"status": "OK", "message": "Fundação funcionando!"})

# 3. Teste do GameLoop
print("\n--- Testando GameLoop (3 segundos) ---")
class MockSystem:
    def __init__(self):
        self.ticks = 0
    def update(self, dt: float):
        self.ticks += 1
        if self.ticks % 60 == 0:
            print(f"Sistema atualizado. Ticks: {self.ticks}, dt: {dt:.4f}")

loop = GameLoop(target_fps=60)
mock_system = MockSystem()
loop.add_system(mock_system)

# Rodar por 3 segundos e parar
import threading
def stop_loop_after_delay(loop, delay):
    time.sleep(delay)
    loop.stop()

timer_thread = threading.Thread(target=stop_loop_after_delay, args=(loop, 3))
timer_thread.start()

loop.start()
print("Teste de GameLoop concluído.")
