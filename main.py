import time
import os
from core.event_bus import bus
from core.game_loop import GameLoop
from core.data_loader import DataLoader
from core.save_manager import SaveManager
from entities.ship import Ship
from systems.universe_manager import UniverseManager
from systems.player_manager import PlayerManager
from systems.energy_manager import EnergyManager
from systems.npc_manager import NPCManager
from systems.loot_manager import LootManager
from systems.economy_manager import EconomyManager
from systems.mission_manager import MissionManager
from systems.faction_manager import FactionManager
from systems.event_manager import EventManager
from systems.universe_generator import UniverseGenerator

class SpaceRPGApp:
    """
    Classe principal que orquestra o MVP do RPG Espacial.
    """
    def __init__(self):
        self.loader = DataLoader(data_dir="data")
        self.save_mgr = SaveManager(save_dir="saves")
        self.universe = UniverseManager()
        self.loot_mgr = LootManager()
        self.econ_mgr = EconomyManager()
        self.mission_mgr = MissionManager()
        self.faction_mgr = FactionManager()
        self.universe_gen = UniverseGenerator()
        self.npc_mgr = NPCManager(self.universe)
        self.event_mgr = EventManager(self.universe, self.faction_mgr)
        
        self.player_mgr = None
        self.energy_mgr = None
        self.npc_ais = []
        
        self.loop = GameLoop(target_fps=60)
        self.loop.add_system(self) # O App também é um sistema

        # Inscrição de eventos globais
        bus.subscribe("LOOT_GENERATED", self.econ_mgr.on_loot_collected)
        bus.subscribe("HEAT_WARNING", lambda h: print(f"\n[ALERTA] Superaquecimento: {h:.1f}%!"))
        bus.subscribe("ADD_CREDITS", self.econ_mgr.add_credits)
        bus.subscribe("MISSION_COMPLETED", lambda m: print(f"\n[MISSÃO CONCLUÍDA] {m['title']}!"))
        bus.subscribe("REPUTATION_CHANGED", lambda d: print(f"[REPUTAÇÃO] {d['faction']}: {d['total']} ({'+' if d['amount']>0 else ''}{d['amount']})"))
        bus.subscribe("DYNAMIC_EVENT_STARTED", lambda e: print(f"\n[EVENTO] {e['description']}"))
        bus.subscribe("WINGMAN_RECRUITED", lambda w: print(f"\n[WINGMAN] Piloto recrutado para sua esquadra!"))

    def start_new_game(self, universe_size: str = "Medium"):
        print(f"\n--- Iniciando Novo Jogo (Universo {universe_size}) ---")
        
        # 0. Gerar Universo Procedural
        num_systems = {"Small": 15, "Medium": 25, "Large": 35, "Giant": 50}.get(universe_size, 25)
        generated_universe = self.universe_gen.generate_universe(num_systems)
        print(f"Gerados {len(generated_universe)} sistemas estelares procedurais.")
        
        # 1. Carregar Nave Inicial
        ship_data = self.loader.load_json("ships.json")["ships"][0]
        player_ship_template = Ship.from_dict(ship_data)
        
        # 2. Spawn no Universo
        player_id = self.universe.spawn_ship(player_ship_template, [0, 0])
        player_ship = self.universe.entities[player_id]
        
        # 3. Configurar Managers do Jogador
        self.player_mgr = PlayerManager(player_ship)
        self.energy_mgr = EnergyManager(player_ship)
        
        # 4. Carregar Dados de Facções
        factions_data = self.loader.load_json("factions.json")["factions"]
        self.faction_mgr.setup_factions(factions_data)

        # 5. Carregar Templates de Missões
        mission_templates = self.loader.load_json("mission_templates.json")["templates"]
        self.mission_mgr.set_templates(mission_templates)
        
        # 6. Gerar uma missão inicial
        self.mission_mgr.generate_mission(faction="United Humans")
        
        # 7. Spawn de um NPC inimigo
        npc_data = self.loader.load_json("ships.json")["ships"][0]
        npc_template = Ship.from_dict(npc_data)
        npc_id = self.universe.spawn_ship(npc_template, [300, 300])
        self.npc_mgr.register_npc(npc_id, initial_state="CHASE")
        
        print(f"Piloto pronto na nave {player_ship.name}.")
        self.loop.start()

    def update(self, dt: float):
        """Loop de atualização principal do App."""
        # Atualiza Sistemas
        self.universe.update(dt)
        if self.player_mgr:
            self.player_mgr.update(dt)
        if self.energy_mgr:
            self.energy_mgr.update(dt)
        
        # O NPCManager e EventManager já escutam o TICK via EventBus, 
        # mas garantimos que o TICK seja emitido se o GameLoop não o fizer.
        # No nosso GameLoop atual, ele emite TICK.

        # HUD de Console (a cada 2 segundos aproximadamente)
        # Usamos uma lógica simples baseada no tempo real para não poluir o console
        if int(time.perf_counter()) % 2 == 0 and int((time.perf_counter() % 1) * 100) < 2:
            self.draw_hud()

    def draw_hud(self):
        if not self.player_mgr: return
        ship = self.player_mgr.ship
        # Limpa o console (funciona em Windows e Linux)
        os.system('cls' if os.name == 'nt' else 'clear')
        print("="*40)
        print(f" SPACE RPG MVP - {ship.name}")
        print("="*40)
        print(f" POS: [{ship.position[0]:.1f}, {ship.position[1]:.1f}] | VEL: {sum(v**2 for v in ship.velocity)**0.5:.1f}")
        print(f" ESCUDOS: {ship.current_shields:.1f}% | CALOR: {ship.current_heat:.1f}%")
        print(f" CRÉDITOS: {self.econ_mgr.player_credits}")
        print("-"*40)
        print(f" PIPS: W:{self.energy_mgr.pips['weapons']} S:{self.energy_mgr.pips['shields']} E:{self.energy_mgr.pips['engines']}")
        print("="*40)
        print(" [Simulação Ativa - Pressione Ctrl+C para Sair]")

if __name__ == "__main__":
    app = SpaceRPGApp()
    try:
        app.start_new_game()
    except KeyboardInterrupt:
        print("\nEncerrando o jogo...")
