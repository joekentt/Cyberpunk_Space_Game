"""
Entry point visual do Cyberpunk Space RPG.

Controles:
  W            acelerar (aumentar throttle / frente)
  S            frear e engatar ré (diminuir throttle)
  A / D        girar o bico esquerda / direita
  Q / E        strafe lateral esquerda / direita (thrusters RCS)
  ESPAÇO       disparar arma primária
  F            acoplar/desacoplar em estação (quando dentro do raio)
  1 / 2 / 3    realocar pip para Weapons / Shields / Engines
  ESC          pausar / voltar na UI da estação
"""

import os
import sys
import json
import math
import pygame

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from core.event_bus import bus
from core.input_config import InputConfig
from core.save_manager import SaveManager
from systems.universe_manager import UniverseManager
from systems.player_manager import PlayerManager
from systems.npc_manager import NPCManager, NPCBehavior
from systems.energy_manager import EnergyManager
from systems.combat_manager import CombatManager, DEFAULT_WEAPONS
from systems.station_manager import StationManager
from systems.loot_manager import LootManager
from systems.mission_manager import MissionManager
from systems.faction_manager import FactionManager
from systems.game_state_serializer import build_save_payload, apply_save_payload
from systems.progression_manager import ProgressionManager, WIN_BOUNTY_COUNT
from visual_engine.procedural_assembler import ProceduralShipAssembler
from visual_engine.station_generator import StationGenerator
from visual_engine.vfx_generator import VFXGenerator, render_projectile
from visual_engine.camera import Camera, ParallaxBackground
from visual_engine.hud import HUD
from visual_engine.station_ui import StationUI
from visual_engine.keybinds_ui import KeybindsUI
from visual_engine.main_menu_ui import MainMenuUI
from visual_engine.pilot_creation_ui import PilotCreationUI
from visual_engine.load_menu_ui import LoadMenuUI
from visual_engine.endgame_ui import EndgameUI
from visual_engine.palette_manager import PaletteManager
from entities.ship import Ship
from entities.station import Station


WIDTH, HEIGHT = 960, 640
BG_COLOR = (8, 8, 18)
STARTING_CREDITS = 50000
DEATH_PENALTY_PCT = 0.10   # perde 10% dos créditos ao morrer
SAVE_SLOT = 1              # Ciclo C: slot único. Multi-slot é do Ciclo D.


class SpaceRPGVisual:
    def __init__(self):
        pygame.init()
        self.screen = pygame.display.set_mode((WIDTH, HEIGHT))
        pygame.display.set_caption("Cyberpunk Space RPG")
        self.clock = pygame.time.Clock()
        self.running = True

        # Estado global do jogo. O jogo ABRE no menu principal — o mundo só é
        # construído ao escolher "novo jogo" ou "carregar" (ver start_new_game /
        # load_game). Estados: "main_menu" | "pilot_creation" | "load_menu" |
        # "playing" | "paused" | "keybinds" | "docked" | "dying".
        self.game_state = "main_menu"
        self._pause_selection = 0
        self.death_timer = 0.0
        self._keybinds_return = "paused"   # para onde voltar ao fechar keybinds
        self._menu_scroll = 0.0            # drift do parallax nas telas de menu

        # Configuração de teclas (carrega de config/keybinds.json, ou padrões)
        self.input_cfg = InputConfig()
        self._keymap = {}            # action -> keycode pygame
        self._rebuild_keymap()

        # Persistência (save/load)
        self.save_mgr = SaveManager(save_dir=os.path.join(os.path.dirname(__file__), "saves"))

        # Dados estáticos reusados a cada novo jogo (carregados uma vez)
        missions_path = os.path.join(os.path.dirname(__file__), "data", "mission_templates.json")
        with open(missions_path, "r", encoding="utf-8") as f:
            all_templates = json.load(f)["templates"]
        self._bounty_templates = [t for t in all_templates if t["type"] == "BOUNTY"]
        factions_path = os.path.join(os.path.dirname(__file__), "data", "factions.json")
        with open(factions_path, "r", encoding="utf-8") as f:
            self._factions_data = json.load(f)["factions"]
        ships_path = os.path.join(os.path.dirname(__file__), "data", "ships.json")
        with open(ships_path, "r", encoding="utf-8") as f:
            self._ships_catalog = json.load(f)["ships"]

        # Textos flutuantes de recompensa: [{text, world_pos, timer, color}, ...]
        self._floating_texts = []
        self.pilot_name = None

        # Sistemas de MUNDO (criados em _build_world_systems; None no menu)
        self.universe = None
        self.npc_mgr = None
        self.combat_mgr = None
        self.station_mgr = None
        self.loot_mgr = None
        self.mission_mgr = None
        self.faction_mgr = None
        self.prog_mgr = None
        self.vfx = None
        self.player_id = None
        self.player_mgr = None
        self.energy_mgr = None

        # Visual persistente (não depende do mundo, criado uma vez só)
        self.assembler = ProceduralShipAssembler()
        self.station_gen = StationGenerator()
        self.palette_mgr = PaletteManager()
        self.camera = Camera(WIDTH, HEIGHT)
        self.parallax = ParallaxBackground(WIDTH, HEIGHT)
        self.hud = HUD(WIDTH, HEIGHT)
        self._station_sprites = {}

        # UI overlay
        ships_data = os.path.join(os.path.dirname(__file__), "data", "ships.json")
        self.station_ui = StationUI(WIDTH, HEIGHT, ships_data)
        self.keybinds_ui = KeybindsUI(
            WIDTH, HEIGHT, self.input_cfg, on_change=self._rebuild_keymap
        )
        self.main_menu_ui = MainMenuUI(WIDTH, HEIGHT)
        self.pilot_creation_ui = PilotCreationUI(WIDTH, HEIGHT)
        self.load_menu_ui = LoadMenuUI(WIDTH, HEIGHT)
        self.endgame_ui = EndgameUI(WIDTH, HEIGHT)

        # Fontes
        self.label_font = pygame.font.SysFont("Consolas", 12)
        self.info_font = pygame.font.SysFont("Consolas", 14)
        self.big_font = pygame.font.SysFont("Consolas", 22, bold=True)

        # Abre direto no menu principal
        self.main_menu_ui.open(self._has_saves())

    # -------------------------------------------------------------- ciclo de vida do mundo

    def _build_world_systems(self):
        """
        (Re)cria TODOS os sistemas que se inscrevem no EventBus.

        O `bus` é global e singleton; os managers se inscrevem no __init__. Se
        recriássemos managers sem limpar, os listeners se ACUMULARIAM (cada
        evento dispararia N vezes). Por isso limpamos o bus aqui antes de
        recriar tudo e re-inscrever os handlers de `self`. É a fonte única de
        verdade para evitar listeners duplicados ao reentrar (novo jogo/load).
        """
        bus._listeners.clear()

        self.universe = UniverseManager()
        self.npc_mgr = NPCManager(self.universe)
        self.combat_mgr = CombatManager(self.universe)
        self.station_mgr = StationManager(self.universe)
        self.loot_mgr = LootManager()

        self.mission_mgr = MissionManager()
        self.mission_mgr.set_templates(self._bounty_templates)

        self.faction_mgr = FactionManager()
        self.faction_mgr.setup_factions(self._factions_data)

        self.vfx = VFXGenerator()
        self.vfx.set_universe(self.universe)

        self.prog_mgr = ProgressionManager()

        self.player_id = None
        self.player_mgr = None
        self.energy_mgr = None
        self._floating_texts = []
        self._station_sprites = {}

        self._subscribe_self()

    def _subscribe_self(self):
        """Inscreve os handlers de integração do próprio jogo no bus."""
        bus.subscribe("DOCKED", self._on_docked)
        bus.subscribe("UNDOCKED", self._on_undocked)
        bus.subscribe("SHIP_PURCHASED", self._on_ship_purchased)
        bus.subscribe("SHIP_DESTROYED", self._on_ship_destroyed)
        bus.subscribe("MISSION_ACCEPT_REQUEST", self._on_mission_accept_request)
        bus.subscribe("ADD_CREDITS", self._on_add_credits)
        bus.subscribe("MISSION_COMPLETED", self._on_mission_completed)
        bus.subscribe("GAME_COMPLETED", self._on_game_completed)

    def _teardown_world(self):
        """Descarta o mundo atual com segurança ao voltar para o menu."""
        bus._listeners.clear()
        self.universe = None
        self.npc_mgr = None
        self.combat_mgr = None
        self.station_mgr = None
        self.loot_mgr = None
        self.mission_mgr = None
        self.faction_mgr = None
        self.prog_mgr = None
        self.vfx = None
        self.player_id = None
        self.player_mgr = None
        self.energy_mgr = None
        self._floating_texts = []

    # -------------------------------------------------------------- novo jogo / carregar / menu

    def start_new_game(self, pilot_name: str):
        """Constrói um mundo novo do zero e entra em jogo."""
        self._build_world_systems()
        self.pilot_name = (pilot_name or "Piloto").strip() or "Piloto"
        self._setup_stations()
        self._spawn_player()
        self._setup_npcs()

        player = self.universe.entities[self.player_id]
        self.camera.offset = [player.position[0] - WIDTH / 2,
                              player.position[1] - HEIGHT / 2]
        self.game_state = "playing"

    def _go_main_menu(self):
        """Volta ao menu principal, descartando o mundo (sem fechar o jogo)."""
        self._teardown_world()
        self.game_state = "main_menu"
        self.main_menu_ui.open(self._has_saves())

    def _has_saves(self) -> bool:
        return len(self.save_mgr.list_saves()) > 0

    @staticmethod
    def _slot_from_filename(fname: str):
        """Extrai o número do slot de 'save_slot_{n}.json' (ou None)."""
        base = os.path.basename(fname)
        if base.startswith("save_slot_") and base.endswith(".json"):
            try:
                return int(base[len("save_slot_"):-len(".json")])
            except ValueError:
                return None
        return None

    def _save_entries(self):
        """Monta a lista de saves para a LoadMenuUI (nome, créditos, data)."""
        entries = []
        for fname in self.save_mgr.list_saves():
            slot = self._slot_from_filename(fname)
            if slot is None:
                continue
            try:
                payload = self.save_mgr.load_game(slot)
            except Exception:
                continue
            entries.append({
                "slot": slot,
                "pilot": payload.get("pilot", {}).get("name", "?"),
                "credits": payload.get("credits", 0),
                "saved_at": payload.get("saved_at"),
            })
        entries.sort(key=lambda e: e["slot"])
        return entries

    def _activate_main_menu(self, action: str):
        if action == "new_game":
            self.pilot_creation_ui.open()
            self.game_state = "pilot_creation"
        elif action == "load":
            self.load_menu_ui.open(self._save_entries())
            self.game_state = "load_menu"
        elif action == "keybinds":
            self.keybinds_ui.open()
            self._keybinds_return = "main_menu"
            self.game_state = "keybinds"
        elif action == "quit":
            self.running = False

    # -------------------------------------------------------------- setup

    def _setup_stations(self):
        hub1 = Station(
            id="station_alpha",
            name="Hub Alpha",
            position=[400, 400],
            faction="United Humans",
            station_class="Hub",
            model_id="hub_alpha",
            services=["shipyard", "repair", "refuel"],
            ship_inventory=["wasp_combat", "albatross_explorer", "mule_trader",
                            "terraformador_ligeiro"],
        )
        self.station_mgr.spawn_station(hub1)

        hub2 = Station(
            id="station_beta",
            name="Hub Beta",
            position=[1600, 900],
            faction="Independent",
            station_class="Hub",
            model_id="hub_alpha",
            services=["shipyard", "repair"],
            ship_inventory=["wasp_combat", "albatross_explorer",
                            "stingray_raider"],
        )
        self.station_mgr.spawn_station(hub2)

        # Fronteira — estação pirata com acesso às melhores naves Tier 2
        hub3 = Station(
            id="station_gamma",
            name="Posto Fronteira",
            position=[2600, 400],
            faction="Pirates",
            station_class="Outpost",
            model_id="hub_alpha",
            services=["shipyard", "repair"],
            ship_inventory=["stingray_raider", "terraformador_ligeiro"],
        )
        self.station_mgr.spawn_station(hub3)

    def _hardpoints_for(self, model_id: str) -> dict:
        """Busca os hardpoints declarados no ships.json por model_id/id."""
        for s in self._ships_catalog:
            if s.get("model_id") == model_id or s.get("id") == model_id:
                return dict(s.get("hardpoints", {}))
        return {}

    def _spawn_player(self):
        template = Ship(
            id="player_skiff",
            name="Skiff Mk I",
            ship_class="Small",
            model_id="starter_skiff",
            mass=120,
            energy_capacity=100,
            heat_dissipation=8,
            max_hp=80, current_hp=80,
            max_shields=100, current_shields=100,
            is_player=True,
            faction="United Humans",
            credits=STARTING_CREDITS,
            hardpoints=self._hardpoints_for("starter_skiff"),
        )
        self.player_id = self.universe.spawn_ship(template, [600, 400])
        player = self.universe.entities[self.player_id]

        # Cria managers se ainda não existem; senão re-aponta para a nova ship
        if self.player_mgr is None:
            self.player_mgr = PlayerManager(player)
            self.energy_mgr = EnergyManager(player)
        else:
            self.player_mgr.ship = player
            self.energy_mgr.ship = player

    def _setup_npcs(self):
        # Pirate spawn is 1200+ px from player (detection_range=1000), so the
        # player must fly toward Hub Beta before encountering it.
        npcs = [
            ("Pirates",     "Small",  "wasp_combat",        100, [1800, 300],
             {"hp": 70, "shields": 80}),
            ("Independent", "Small",  "albatross_explorer", 130, [200, 200],
             {"hp": 75, "shields": 90}),
            ("Independent", "Medium", "mule_trader",        350, [200, 700],
             {"hp": 200, "shields": 150}),
        ]
        for faction, ship_class, model_id, mass, pos, stats in npcs:
            template = Ship(
                id=f"npc_{faction}_{model_id}_{len(self.universe.entities)}",
                name=f"{faction}-{model_id}",
                ship_class=ship_class,
                model_id=model_id,
                mass=mass,
                energy_capacity=100,
                heat_dissipation=5,
                max_hp=stats["hp"], current_hp=stats["hp"],
                max_shields=stats["shields"], current_shields=stats["shields"],
                faction=faction,
                hardpoints=self._hardpoints_for(model_id),
            )
            sid = self.universe.spawn_ship(template, list(pos))
            self.npc_mgr.register_npc(sid, initial_state=NPCBehavior.IDLE)

    # -------------------------------------------------------------- input config

    def _rebuild_keymap(self):
        """(Re)constrói o dict action -> keycode a partir do InputConfig."""
        self._keymap = {}
        for action in self.input_cfg.ACTIONS:
            name = self.input_cfg.get(action)
            try:
                self._keymap[action] = pygame.key.key_code(name)
            except (ValueError, TypeError):
                # Nome inválido: cai no default da ação para não quebrar o input
                default = self.input_cfg.DEFAULTS[action]
                self._keymap[action] = pygame.key.key_code(default)

    def _key(self, action: str) -> int:
        """Keycode pygame atualmente ligado a uma ação."""
        return self._keymap.get(action, -1)

    def _pause_options(self):
        """Opções do menu de pausa: (rótulo, chave de ação)."""
        return [
            ("CONTINUAR", "resume"),
            ("SALVAR JOGO", "save"),
            ("SALVAR E SAIR PARA O MENU", "save_quit_menu"),
            ("CONFIGURAR TECLAS", "keybinds"),
            ("SAIR DO JOGO", "quit"),
        ]

    def _activate_pause_option(self, key: str):
        if key == "resume":
            self.game_state = "playing"
        elif key == "save":
            self._save_game()
            self.game_state = "playing"
        elif key == "save_quit_menu":
            self._save_game()
            self._go_main_menu()
        elif key == "keybinds":
            self.keybinds_ui.open()
            self._keybinds_return = "paused"
            self.game_state = "keybinds"
        elif key == "quit":
            self.running = False

    # -------------------------------------------------------------- save / load

    def _save_game(self, slot: int = SAVE_SLOT):
        """Monta o payload (inclui o piloto) e grava no slot."""
        player = self.universe.entities.get(self.player_id) if self.universe else None
        if not player:
            return
        payload = build_save_payload(
            player_ship=player,
            pips=self.player_mgr.pips,
            mission_mgr=self.mission_mgr,
            faction_mgr=self.faction_mgr,
            last_docked_station_id=self.station_mgr.last_docked_station_id,
            camera_offset=list(self.camera.offset),
            pilot={"name": self.pilot_name or "Piloto"},
            progression=self.prog_mgr.get_save_data() if self.prog_mgr else {},
        )
        self.save_mgr.save_game(slot, payload)
        self._floating_texts.append({
            "text": "JOGO SALVO",
            "pos": list(player.position),
            "timer": 2.2,
            "color": (120, 220, 255),
        })

    def load_game(self, slot: int = SAVE_SLOT) -> bool:
        """
        Carrega um save e RECONSTRÓI o mundo a partir dele.

        Chamado pelo menu de carregar (Ciclo D) e também pela tecla de debug F9
        durante o jogo. Reconstrói os managers (limpando o bus — sem listeners
        duplicados), recria estações/NPCs e aplica o estado salvo do jogador.
        Retorna True se carregou.
        """
        try:
            payload = self.save_mgr.load_game(slot)
        except (FileNotFoundError, ValueError):
            return False

        # Mundo novo do zero, depois aplica o estado salvo por cima.
        self._build_world_systems()
        self._setup_stations()
        self._setup_npcs()
        self._spawn_player()   # cria managers + player placeholder

        self.player_id = apply_save_payload(
            payload=payload,
            universe=self.universe,
            player_mgr=self.player_mgr,
            energy_mgr=self.energy_mgr,
            mission_mgr=self.mission_mgr,
            faction_mgr=self.faction_mgr,
            station_mgr=self.station_mgr,
            old_player_id=self.player_id,
        )
        self.pilot_name = payload.get("pilot", {}).get("name", "Piloto")
        self.station_ui.player = self.universe.entities[self.player_id]
        self.prog_mgr.load_save_data(payload.get("progression", {}))

        offset = payload.get("camera_offset")
        if offset:
            self.camera.offset = list(offset)

        self.game_state = "playing"
        player = self.universe.entities[self.player_id]
        self._floating_texts.append({
            "text": "JOGO CARREGADO",
            "pos": list(player.position),
            "timer": 2.2,
            "color": (120, 255, 180),
        })
        return True

    # -------------------------------------------------------------- input

    def _handle_input(self):
        for ev in pygame.event.get():
            if ev.type == pygame.QUIT:
                self.running = False
                continue

            # ---- Telas de moldura (menu principal, criação, carregar) ----
            if self.game_state == "main_menu":
                action = self.main_menu_ui.handle_event(ev)
                if action:
                    self._activate_main_menu(action)
                continue

            if self.game_state == "pilot_creation":
                res = self.pilot_creation_ui.handle_event(ev)
                if res == "confirm":
                    self.start_new_game(self.pilot_creation_ui.name)
                elif res == "cancel":
                    self._go_main_menu()
                continue

            if self.game_state == "load_menu":
                res = self.load_menu_ui.handle_event(ev)
                if isinstance(res, tuple) and res[0] == "load":
                    if not self.load_game(res[1]):
                        # falhou — volta ao menu (não deveria ocorrer)
                        self._go_main_menu()
                elif res == "back":
                    self._go_main_menu()
                continue

            # UI da estação consome eventos quando acoplado
            if self.game_state == "docked":
                if self.station_ui.handle_event(ev):
                    continue
                # ESC no menu principal da estação: ignorar (nunca fecha o jogo)
                if ev.type == pygame.KEYDOWN and ev.key == pygame.K_ESCAPE:
                    continue

            # Tela de configuração de teclas consome todos os eventos.
            # Pode ter sido aberta pelo menu de pausa OU pelo menu principal —
            # _keybinds_return diz para onde voltar.
            if self.game_state == "keybinds":
                if self.keybinds_ui.handle_event(ev) == "close":
                    self.game_state = self._keybinds_return
                    if self._keybinds_return == "paused":
                        self._pause_selection = 0
                    elif self._keybinds_return == "main_menu":
                        self.main_menu_ui.open(self._has_saves())
                continue

            if ev.type != pygame.KEYDOWN:
                continue

            # Tela de fim de jogo
            if self.game_state == "endgame":
                res = self.endgame_ui.handle_event(ev)
                if res == "menu":
                    self._go_main_menu()
                elif res == "continue":
                    self.game_state = "playing"
                continue

            # Tecla de pausa (configurável) abre o menu durante o jogo
            if self.game_state == "playing" and ev.key == self._key("pause"):
                self.game_state = "paused"
                self._pause_selection = 0
                continue

            # Navegação do menu de pausa
            if self.game_state == "paused":
                opts = self._pause_options()
                # ESC ou a tecla de pausa retomam o jogo
                if ev.key == pygame.K_ESCAPE or ev.key == self._key("pause"):
                    self.game_state = "playing"
                elif ev.key == pygame.K_UP:
                    self._pause_selection = (self._pause_selection - 1) % len(opts)
                elif ev.key == pygame.K_DOWN:
                    self._pause_selection = (self._pause_selection + 1) % len(opts)
                elif ev.key in (pygame.K_RETURN, pygame.K_KP_ENTER):
                    self._activate_pause_option(opts[self._pause_selection][1])
                continue

            if self.game_state != "playing":
                continue

            # Tecla de debug para carregar o save (Ciclo D dará UI dedicada)
            if ev.key == pygame.K_F9:
                self.load_game()
                continue

            if ev.key == self._key("dock_toggle"):
                bus.emit("PLAYER_INPUT", {"action": "dock_toggle"})
            elif ev.key == pygame.K_1:
                bus.emit("PLAYER_INPUT", {"action": "set_pips", "system": "weapons"})
            elif ev.key == pygame.K_2:
                bus.emit("PLAYER_INPUT", {"action": "set_pips", "system": "shields"})
            elif ev.key == pygame.K_3:
                bus.emit("PLAYER_INPUT", {"action": "set_pips", "system": "engines"})

        # Inputs contínuos só durante "playing"
        if self.game_state != "playing":
            return

        keys = pygame.key.get_pressed()
        player = self.universe.entities.get(self.player_id)
        if keys[self._key("thrust_forward")]:
            bus.emit("PLAYER_INPUT", {"action": "thrust", "value": 1.0})
            if player:
                palette = self.palette_mgr.get_palette(player.faction)
                self.vfx.create_engine_trail(
                    tuple(player.position), player.rotation, palette["accent"][:3]
                )
        if keys[self._key("thrust_back")]:
            # Throttle negativo: freia e, no ponto morto, engata ré
            bus.emit("PLAYER_INPUT", {"action": "thrust", "value": -1.0})
            if player:
                self._rcs_vfx(player, "reverse")
        if keys[self._key("rotate_left")]:
            bus.emit("PLAYER_INPUT", {"action": "rotate", "value": -1.0})
        if keys[self._key("rotate_right")]:
            bus.emit("PLAYER_INPUT", {"action": "rotate", "value": 1.0})
        if keys[self._key("strafe_left")]:
            bus.emit("PLAYER_INPUT", {"action": "strafe", "value": -1.0})
            if player:
                self._rcs_vfx(player, "strafe", direction=-1.0)
        if keys[self._key("strafe_right")]:
            bus.emit("PLAYER_INPUT", {"action": "strafe", "value": 1.0})
            if player:
                self._rcs_vfx(player, "strafe", direction=1.0)
        if keys[self._key("shoot")]:
            bus.emit("PLAYER_INPUT", {"action": "shoot", "value": 1.0})

    def _rcs_vfx(self, player, kind: str, direction: float = 0.0):
        """
        Cria o jato de RCS (ré ou strafe) coerente com a física do
        PlayerManager. Usa a mesma matemática de vetor perpendicular
        (right = (-fy, fx)) para posicionar a origem do jato.
        """
        palette = self.palette_mgr.get_palette(player.faction)
        color = palette["accent"][:3]
        rad = math.radians(player.rotation)
        forward = (math.cos(rad), math.sin(rad))
        right = (-forward[1], forward[0])
        px, py = player.position

        if kind == "reverse":
            # RCS de freio no nariz: o gás escapa pela FRENTE, empurrando a
            # nave para trás. Origem no bico, jato na direção do bico.
            nose = 16
            origin = (px + forward[0] * nose, py + forward[1] * nose)
            jet_dir = math.degrees(math.atan2(forward[1], forward[0]))
            self.vfx.create_rcs_puff(origin, jet_dir, color, strength="reverse")
        else:  # strafe: jato sai do lado OPOSTO ao movimento
            side = 12
            if direction > 0:   # strafe à direita (E): jato sai da esquerda
                origin = (px - right[0] * side, py - right[1] * side)
                jet = (-right[0], -right[1])
            else:               # strafe à esquerda (Q): jato sai da direita
                origin = (px + right[0] * side, py + right[1] * side)
                jet = (right[0], right[1])
            jet_dir = math.degrees(math.atan2(jet[1], jet[0]))
            self.vfx.create_rcs_puff(origin, jet_dir, color, strength="strafe")

    # -------------------------------------------------------------- bus listeners

    def _on_docked(self, data):
        station = data["station"]
        self.game_state = "docked"
        player = self.universe.entities.get(self.player_id)
        if player:
            player.velocity = [0.0, 0.0]

        # Gera 2 missões novas para esta estação (substitui as anteriores)
        self.mission_mgr.available_missions.clear()
        for _ in range(2):
            self.mission_mgr.generate_mission(
                faction=station.faction, difficulty=1.0
            )
        available = list(self.mission_mgr.available_missions.values())
        self.station_ui.open(station, player, available_missions=available)

    def _on_undocked(self, data):
        self.game_state = "playing"
        self.station_ui.close()

    def _on_ship_purchased(self, data):
        """Substitui a Ship do player pela nova nave comprada."""
        ship_data = data["ship_data"]
        player = self.universe.entities.get(self.player_id)
        if not player:
            return
        # Preserva créditos e facção e posição
        new_template = Ship.from_dict(ship_data)
        new_template.is_player = True
        new_template.credits = player.credits
        new_template.faction = player.faction

        # Remove a ship antiga e spawn da nova na mesma posição.
        # remove_entity emite ENTITY_REMOVED para limpar referências no NPCManager.
        old_pos = list(player.position)
        self.universe.remove_entity(self.player_id)
        self.player_id = self.universe.spawn_ship(new_template, old_pos)
        new_player = self.universe.entities[self.player_id]

        # Re-aponta managers para a nova ship
        self.player_mgr.ship = new_player
        # PlayerManager adiciona 'pips' dinamicamente no __init__; a nova Ship
        # criada por spawn_ship não tem esse atributo — restauramos aqui.
        new_player.pips = dict(self.player_mgr.pips)
        self.energy_mgr.ship = new_player

        # Atualiza referência na UI
        self.station_ui.player = new_player

    def _on_ship_destroyed(self, data):
        ship_id = data["ship_id"]
        attacker_id = data.get("attacker_id")
        destroyed_faction = data.get("faction", "")

        if ship_id == self.player_id:
            self.game_state = "dying"
            self.death_timer = 3.0
            return

        # Recompensa e progresso de missão apenas se o player foi o autor do abate
        if attacker_id != self.player_id:
            return

        loot = self.loot_mgr.generate_loot(data.get("ship_class", "Small"))
        credits_won = loot["credits"]
        player = self.universe.entities.get(self.player_id)
        if player:
            player.credits += credits_won
            self._floating_texts.append({
                "text": f"+{credits_won} cr",
                "pos": list(data.get("position", player.position)),
                "timer": 2.2,
                "color": (255, 215, 0),
            })

        # Registra o kill nas missões ativas (bounty por facção)
        if destroyed_faction:
            self.mission_mgr.record_kill(destroyed_faction)

    def _on_mission_accept_request(self, data):
        mission_id = data.get("mission_id")
        if mission_id:
            self.mission_mgr.accept_mission(mission_id)

    def _on_add_credits(self, amount):
        player = self.universe.entities.get(self.player_id)
        if player:
            player.credits += amount
            self._floating_texts.append({
                "text": f"+{amount} cr",
                "pos": list(player.position),
                "timer": 2.2,
                "color": (120, 255, 120),
            })

    def _on_mission_completed(self, data):
        self._floating_texts.append({
            "text": f"MISSÃO COMPLETA! +{data.get('reward_credits', 0)} cr",
            "pos": list(self.universe.entities[self.player_id].position)
                   if self.player_id in self.universe.entities else [0, 0],
            "timer": 3.5,
            "color": (80, 255, 180),
        })

    def _on_game_completed(self, data):
        self.game_state = "endgame"
        self.endgame_ui.open(self.pilot_name)

    # -------------------------------------------------------------- respawn

    def _respawn(self):
        """Respawn do jogador em uma estação com Skiff básica."""
        # Buscar última estação atracada (ou primeira disponível)
        station = self.station_mgr.get_respawn_station()
        spawn_pos = [station.position[0] + 200, station.position[1]] if station \
                    else [WIDTH / 2, HEIGHT / 2]

        # Preservar créditos com penalidade
        prev_credits = 0
        old_player = self.universe.entities.get(self.player_id)
        if old_player:
            prev_credits = old_player.credits
        else:
            # já foi removido pelo CombatManager — usar valor padrão de death
            prev_credits = STARTING_CREDITS  # fallback (não deve ocorrer normalmente)

        new_credits = int(prev_credits * (1 - DEATH_PENALTY_PCT))

        # Spawn de Skiff básica (penalidade: perde a nave atual)
        template = Ship(
            id="player_skiff",
            name="Skiff Mk I",
            ship_class="Small",
            model_id="starter_skiff",
            mass=120,
            energy_capacity=100,
            heat_dissipation=8,
            max_hp=80, current_hp=80,
            max_shields=100, current_shields=100,
            is_player=True,
            faction="United Humans",
            credits=new_credits,
            hardpoints=self._hardpoints_for("starter_skiff"),
        )
        # Garante que o slot do player não está mais ocupado
        if self.player_id in self.universe.entities:
            del self.universe.entities[self.player_id]

        self.player_id = self.universe.spawn_ship(template, spawn_pos)
        new_player = self.universe.entities[self.player_id]

        self.player_mgr.ship = new_player
        new_player.pips = dict(self.player_mgr.pips)  # restore pips mirror for HUD
        self.energy_mgr.ship = new_player

        self.game_state = "playing"

    # -------------------------------------------------------------- loop

    def run(self):
        while self.running:
            dt = self.clock.tick(60) / 1000.0
            self._handle_input()

            # Telas de moldura: anima o fundo estelar e o caret do input
            if self.game_state in ("main_menu", "pilot_creation", "load_menu") or \
                    (self.game_state == "keybinds" and self._keybinds_return == "main_menu"):
                self._menu_scroll += 12.0 * dt
                if self.game_state == "pilot_creation":
                    self.pilot_creation_ui.update(dt)
                self._render()
                continue

            # Update
            if self.game_state == "playing":
                self.universe.update(dt)
                if self.player_id in self.universe.entities:
                    self.player_mgr.update(dt)
                    self.energy_mgr.update(dt)
                self.npc_mgr.update(dt)
                self.combat_mgr.update(dt)
                self.vfx.update(dt)

                player = self.universe.entities.get(self.player_id)
                if player:
                    self.camera.follow(player.position, dt)
                    self.station_mgr.update(dt, player.position)

            elif self.game_state == "endgame":
                self.vfx.update(dt)

            elif self.game_state == "docked":
                self.station_ui.update(dt)
                # VFX continua atualizando pra não congelar partículas
                self.vfx.update(dt)

            elif self.game_state == "dying":
                self.death_timer -= dt
                self.vfx.update(dt)
                self.universe.update(dt)
                if self.death_timer <= 0:
                    self._respawn()

            # Textos flutuantes decaem independente do game_state
            self._floating_texts = [
                {**ft, "timer": ft["timer"] - dt, "pos": [ft["pos"][0], ft["pos"][1] - 24 * dt]}
                for ft in self._floating_texts
                if ft["timer"] - dt > 0
            ]

            self._render()

        pygame.quit()

    def _render(self):
        self.screen.fill(BG_COLOR)

        # ---- Telas de moldura: fundo estelar com drift + a UI por cima ----
        menu_keybinds = (self.game_state == "keybinds"
                         and self._keybinds_return == "main_menu")
        if self.game_state in ("main_menu", "pilot_creation", "load_menu") or menu_keybinds:
            self.parallax.draw(self.screen, (self._menu_scroll, self._menu_scroll * 0.6))
            if self.game_state == "main_menu":
                self.main_menu_ui.draw(self.screen)
            elif self.game_state == "pilot_creation":
                self.pilot_creation_ui.draw(self.screen)
            elif self.game_state == "load_menu":
                self.load_menu_ui.draw(self.screen)
            elif menu_keybinds:
                self.keybinds_ui.draw(self.screen)
            self._draw_fps()
            pygame.display.flip()
            return

        self.parallax.draw(self.screen, self.camera.offset)

        # Estações (atrás de tudo)
        for station in self.station_mgr.get_all():
            self._draw_station(station)

        # VFX (atrás das naves)
        self.vfx.draw(self.screen, self.camera.offset)

        # Naves
        for entity_id, entity in list(self.universe.entities.items()):
            self._draw_entity(entity_id, entity)

        # Projéteis
        for proj in self.combat_mgr.projectiles.values():
            if proj.alive:
                rot = math.degrees(math.atan2(proj.velocity[1], proj.velocity[0]))
                render_projectile(
                    self.screen, proj.position, proj.color, proj.weapon_type,
                    self.camera.offset, rotation=rot
                )

        # Textos flutuantes de recompensa (espaço de mundo → espaço de tela)
        for ft in self._floating_texts:
            alpha = min(255, int(255 * ft["timer"] / 2.2))
            sx = int(ft["pos"][0] - self.camera.offset[0])
            sy = int(ft["pos"][1] - self.camera.offset[1])
            surf = self.info_font.render(ft["text"], True, ft["color"])
            surf.set_alpha(alpha)
            self.screen.blit(surf, surf.get_rect(center=(sx, sy)))

        player = self.universe.entities.get(self.player_id)

        # HUD durante gameplay (mostra também em pausa para o fundo ficar visível)
        if self.game_state in ("playing", "paused") and player:
            self.hud.draw(self.screen, player)
            self._draw_combat_hud(player)
            self._draw_docking_prompt()

        if self.game_state == "paused":
            self._draw_pause_menu()
        elif self.game_state == "keybinds":
            self.keybinds_ui.draw(self.screen)
        elif self.game_state == "docked":
            self.station_ui.draw(self.screen)
        elif self.game_state == "dying":
            self._draw_dying_overlay()
        elif self.game_state == "endgame":
            self.endgame_ui.draw(self.screen)

        self._draw_controls()
        self._draw_fps()
        pygame.display.flip()

    # -------------------------------------------------------------- draw helpers

    def _draw_station(self, station):
        # Cache do sprite por (model_id, faction)
        cache_key = (station.model_id, station.faction)
        if cache_key not in self._station_sprites:
            palette = self.palette_mgr.get_palette(station.faction)
            pil_img = self.station_gen.generate_station_sprite(
                station.model_id, palette, seed=hash(station.id) % 10000
            )
            mode = pil_img.mode
            size = pil_img.size
            data = pil_img.tobytes()
            surf = pygame.image.fromstring(data, size, mode).convert_alpha()
            self._station_sprites[cache_key] = surf

        sprite = self._station_sprites[cache_key]
        sx = station.position[0] - self.camera.offset[0] - sprite.get_width() / 2
        sy = station.position[1] - self.camera.offset[1] - sprite.get_height() / 2
        self.screen.blit(sprite, (sx, sy))

        # Anel decorativo do raio de docking (aparece quando próximo)
        player = self.universe.entities.get(self.player_id)
        if player and self.game_state == "playing":
            d = station.distance_to(player.position)
            if d < station.docking_radius * 1.5:
                cx = int(station.position[0] - self.camera.offset[0])
                cy = int(station.position[1] - self.camera.offset[1])
                # cor verde se dentro do raio, ciano apagado se quase
                alpha = max(40, int(120 - (d / station.docking_radius) * 60))
                color = (60, 220, 120) if d < station.docking_radius else (60, 150, 200)
                surf = pygame.Surface(self.screen.get_size(), pygame.SRCALPHA)
                pygame.draw.circle(surf, (*color, alpha),
                                   (cx, cy), int(station.docking_radius), width=1)
                self.screen.blit(surf, (0, 0))

    def _draw_entity(self, entity_id, entity):
        seed = abs(hash(entity_id)) % 10000
        sprite = self.assembler.get_ship_sprite(entity, seed)
        rotated = pygame.transform.rotate(sprite, -entity.rotation)
        screen_x = entity.position[0] - self.camera.offset[0]
        screen_y = entity.position[1] - self.camera.offset[1]
        rect = rotated.get_rect(center=(int(screen_x), int(screen_y)))
        self.screen.blit(rotated, rect)

        if not getattr(entity, "is_player", False):
            hp_ratio = entity.current_hp / entity.max_hp if entity.max_hp > 0 else 0
            sh_ratio = entity.current_shields / entity.max_shields if entity.max_shields > 0 else 0
            self._draw_health_bar(rect.centerx, rect.top - 8, hp_ratio, sh_ratio,
                                  faction=getattr(entity, "faction", "Independent"))
            label = self.label_font.render(entity.faction, True, (180, 200, 220))
            self.screen.blit(label, (rect.centerx - label.get_width() // 2, rect.top - 22))

    def _draw_health_bar(self, cx, cy, hp_ratio, sh_ratio, faction):
        w, h = 36, 3
        gap = 1
        pygame.draw.rect(self.screen, (30, 30, 50), (cx - w // 2, cy - h - gap, w, h))
        pygame.draw.rect(self.screen, (60, 160, 255),
                         (cx - w // 2, cy - h - gap, int(w * max(0, sh_ratio)), h))
        hp_color = (60, 230, 80) if hp_ratio > 0.5 else \
                   ((255, 200, 60) if hp_ratio > 0.25 else (255, 70, 50))
        pygame.draw.rect(self.screen, (40, 30, 30), (cx - w // 2, cy, w, h))
        pygame.draw.rect(self.screen, hp_color,
                         (cx - w // 2, cy, int(w * max(0, hp_ratio)), h))

    def _draw_combat_hud(self, player):
        cd_key = f"{player.id}:kinetic_small"
        cd = self.combat_mgr.cooldowns.get(cd_key, 0.0)
        max_cd = DEFAULT_WEAPONS["kinetic_small"]["cooldown"]
        ratio = cd / max_cd if max_cd > 0 else 0
        bar_x, bar_y = 20, HEIGHT - 50
        pygame.draw.rect(self.screen, (40, 40, 50), (bar_x, bar_y, 160, 8))
        if ratio > 0:
            pygame.draw.rect(self.screen, (255, 200, 60),
                             (bar_x, bar_y, int(160 * (1 - ratio)), 8))
        else:
            pygame.draw.rect(self.screen, (80, 255, 100),
                             (bar_x, bar_y, 160, 8))
        label = self.label_font.render("WEAPON" + ("" if cd == 0 else f" ({cd:.2f}s)"),
                                       True, (200, 220, 240))
        self.screen.blit(label, (bar_x + 168, bar_y - 2))
        hp_text = f"HULL: {int(player.current_hp)}/{int(player.max_hp)}"
        sh_text = f"SHIELDS: {int(player.current_shields)}/{int(player.max_shields)}"
        cr_text = f"CR: {player.credits:,}".replace(",", ".")
        self.screen.blit(self.label_font.render(hp_text, True, (255, 130, 90)),
                         (bar_x, bar_y - 22))
        self.screen.blit(self.label_font.render(sh_text, True, (90, 180, 255)),
                         (bar_x, bar_y - 36))
        self.screen.blit(self.label_font.render(cr_text, True, (255, 220, 80)),
                         (bar_x, bar_y - 50))
        self.screen.blit(
            self.label_font.render(f"NAVE: {player.name}", True, (180, 200, 220)),
            (bar_x, bar_y - 64)
        )
        if self.pilot_name:
            self.screen.blit(
                self.label_font.render(f"PILOTO: {self.pilot_name}", True, (160, 200, 255)),
                (bar_x, bar_y - 78)
            )

        # Progresso de vitória (Ciclo E)
        hud_y = bar_y - 96
        if self.prog_mgr:
            bc = self.prog_mgr.bounties_completed
            if self.prog_mgr.game_completed:
                prog_text = f"OBJETIVO: CONCLUÍDO ({bc}/{WIN_BOUNTY_COUNT})"
                prog_color = (80, 255, 180)
            else:
                prog_text = f"OBJETIVO: {bc}/{WIN_BOUNTY_COUNT} bounties"
                prog_color = (200, 200, 100)
            self.screen.blit(
                self.label_font.render(prog_text, True, prog_color),
                (bar_x, hud_y)
            )
            hud_y -= 14

        # Missões ativas
        for mission in self.mission_mgr.active_missions.values():
            kill_obj = next(
                (o for o in mission.objectives if o.get("type") == "KILL"), None
            )
            if kill_obj:
                prog = mission.kill_progress
                req = kill_obj.get("count", 1)
                faction = kill_obj.get("target_faction", "?")
                text = f"BOUNTY: {faction} {prog}/{req}"
                color = (80, 255, 160) if prog >= req else (255, 220, 80)
                self.screen.blit(
                    self.label_font.render(text, True, color),
                    (bar_x, hud_y)
                )
                hud_y -= 14

    def _draw_docking_prompt(self):
        if self.station_mgr.docking_state == "approach":
            station = self.station_mgr.stations[self.station_mgr.current_station_id]
            text = self.big_font.render(
                f"[F] Acoplar em {station.name}", True, (60, 220, 120)
            )
            rect = text.get_rect(center=(WIDTH // 2, HEIGHT - 100))
            bg = pygame.Surface((rect.w + 24, rect.h + 12), pygame.SRCALPHA)
            bg.fill((0, 0, 0, 180))
            self.screen.blit(bg, (rect.x - 12, rect.y - 6))
            self.screen.blit(text, rect)

    def _draw_dying_overlay(self):
        overlay = pygame.Surface((WIDTH, HEIGHT), pygame.SRCALPHA)
        overlay.fill((30, 0, 0, 150))
        self.screen.blit(overlay, (0, 0))
        text = self.big_font.render("NAVE DESTRUÍDA", True, (255, 60, 60))
        self.screen.blit(text, text.get_rect(center=(WIDTH // 2, HEIGHT // 2 - 20)))
        sub = self.info_font.render(
            f"Respawnando em {self.death_timer:.0f}s...",
            True, (200, 200, 200)
        )
        self.screen.blit(sub, sub.get_rect(center=(WIDTH // 2, HEIGHT // 2 + 18)))
        loss = self.label_font.render(
            f"Penalidade: -{int(DEATH_PENALTY_PCT * 100)}% créditos · Volta com Skiff Mk I",
            True, (180, 160, 160)
        )
        self.screen.blit(loss, loss.get_rect(center=(WIDTH // 2, HEIGHT // 2 + 42)))

    def _draw_pause_menu(self):
        overlay = pygame.Surface((WIDTH, HEIGHT), pygame.SRCALPHA)
        overlay.fill((0, 0, 0, 160))
        self.screen.blit(overlay, (0, 0))

        title = self.big_font.render("PAUSADO", True, (0, 220, 255))
        self.screen.blit(title, title.get_rect(center=(WIDTH // 2, HEIGHT // 2 - 60)))

        options = self._pause_options()
        for i, (label, _) in enumerate(options):
            color = (255, 220, 120) if i == self._pause_selection else (180, 200, 220)
            prefix = "▸ " if i == self._pause_selection else "  "
            text = self.info_font.render(prefix + label, True, color)
            self.screen.blit(text, text.get_rect(center=(WIDTH // 2, HEIGHT // 2 + i * 36)))

        hint = self.label_font.render(
            "ESC = continuar   ↑↓ = navegar   ENTER = confirmar",
            True, (120, 140, 160),
        )
        self.screen.blit(hint, hint.get_rect(center=(WIDTH // 2, HEIGHT // 2 + 96)))

    def _draw_controls(self):
        if self.game_state in ("docked", "paused", "keybinds"):
            return  # UI da estação / pausa / keybinds cuida do próprio help
        lines = [
            "W/S = throttle (frente/ré)",
            "A/D = girar    Q/E = strafe",
            "ESPAÇO = disparar    F = acoplar",
            "1/2/3 = realocar PIP",
            "ESC = pausar (salvar)    F9 = carregar",
        ]
        y = HEIGHT - 80
        for line in lines:
            img = self.label_font.render(line, True, (140, 160, 180))
            self.screen.blit(img, (WIDTH - img.get_width() - 12, y))
            y += 14

    def _draw_fps(self):
        fps = self.clock.get_fps()
        img = self.label_font.render(f"FPS: {fps:.0f}", True, (100, 120, 140))
        self.screen.blit(img, (WIDTH - 80, 8))


def main():
    headless = os.environ.get("SDL_VIDEODRIVER") == "dummy"
    game = SpaceRPGVisual()
    if headless:
        # O jogo abre no menu; o smoke valida o boot do menu e depois um
        # mundo recém-iniciado.
        assert game.game_state == "main_menu" and game.player_id is None
        game._render()  # desenha o menu uma vez
        game.start_new_game("Smoke")
        for i in range(60):
            game.clock.tick(60)
            game.universe.update(1 / 60)
            if game.player_id in game.universe.entities:
                game.player_mgr.update(1 / 60)
                game.energy_mgr.update(1 / 60)
            game.npc_mgr.update(1 / 60)
            game.combat_mgr.update(1 / 60)
            game.vfx.update(1 / 60)
            player = game.universe.entities.get(game.player_id)
            if player:
                game.camera.follow(player.position, 1 / 60)
                game.station_mgr.update(1 / 60, player.position)
            game._render()
        print(f"OK — menu boot + {len(game.universe.entities)} naves, "
              f"{len(game.station_mgr.stations)} estações")
        pygame.quit()
        return
    game.run()


if __name__ == "__main__":
    main()
