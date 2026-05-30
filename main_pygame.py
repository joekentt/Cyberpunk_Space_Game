"""
Entry point visual do Cyberpunk Space RPG.

Controles:
  W            acelerar
  A / D        rotacionar esquerda / direita
  ESPAÇO       disparar arma primária
  F            acoplar/desacoplar em estação (quando dentro do raio)
  1 / 2 / 3    realocar pip para Weapons / Shields / Engines
  ESC          pausar / voltar na UI da estação
"""

import os
import sys
import math
import pygame

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from core.event_bus import bus
from systems.universe_manager import UniverseManager
from systems.player_manager import PlayerManager
from systems.npc_manager import NPCManager, NPCBehavior
from systems.energy_manager import EnergyManager
from systems.combat_manager import CombatManager, DEFAULT_WEAPONS
from systems.station_manager import StationManager
from visual_engine.procedural_assembler import ProceduralShipAssembler
from visual_engine.station_generator import StationGenerator
from visual_engine.vfx_generator import VFXGenerator, render_projectile
from visual_engine.camera import Camera, ParallaxBackground
from visual_engine.hud import HUD
from visual_engine.station_ui import StationUI
from visual_engine.palette_manager import PaletteManager
from entities.ship import Ship
from entities.station import Station


WIDTH, HEIGHT = 960, 640
BG_COLOR = (8, 8, 18)
STARTING_CREDITS = 50000
DEATH_PENALTY_PCT = 0.10   # perde 10% dos créditos ao morrer


class SpaceRPGVisual:
    def __init__(self):
        pygame.init()
        self.screen = pygame.display.set_mode((WIDTH, HEIGHT))
        pygame.display.set_caption("Cyberpunk Space RPG")
        self.clock = pygame.time.Clock()
        self.running = True

        # Estado global do jogo
        # "playing" | "paused" | "docked" | "dying" (animação curta de morte)
        self.game_state = "playing"
        self._pause_selection = 0   # 0 = Continuar, 1 = Sair do jogo
        self.death_timer = 0.0

        # Lógica
        self.universe = UniverseManager()
        self.npc_mgr = NPCManager(self.universe)
        self.combat_mgr = CombatManager(self.universe)
        self.station_mgr = StationManager(self.universe)

        self.player_id = None
        self.player_mgr = None
        self.energy_mgr = None

        self._setup_stations()
        self._spawn_player()
        self._setup_npcs()

        # Visual
        self.assembler = ProceduralShipAssembler()
        self.station_gen = StationGenerator()
        self.palette_mgr = PaletteManager()
        self.vfx = VFXGenerator()
        self.vfx.set_universe(self.universe)
        self.camera = Camera(WIDTH, HEIGHT)
        self.parallax = ParallaxBackground(WIDTH, HEIGHT)
        self.hud = HUD(WIDTH, HEIGHT)

        # Cache de sprites de estação
        self._station_sprites = {}

        # UI overlay
        ships_data = os.path.join(os.path.dirname(__file__), "data", "ships.json")
        self.station_ui = StationUI(WIDTH, HEIGHT, ships_data)

        # Fontes
        self.label_font = pygame.font.SysFont("Consolas", 12)
        self.info_font = pygame.font.SysFont("Consolas", 14)
        self.big_font = pygame.font.SysFont("Consolas", 22, bold=True)

        # Bus listeners para integração
        bus.subscribe("DOCKED", self._on_docked)
        bus.subscribe("UNDOCKED", self._on_undocked)
        bus.subscribe("SHIP_PURCHASED", self._on_ship_purchased)
        bus.subscribe("SHIP_DESTROYED", self._on_ship_destroyed)

    # -------------------------------------------------------------- setup

    def _setup_stations(self):
        # Duas estações no mapa para o jogador ter pra onde ir
        hub1 = Station(
            id="station_alpha",
            name="Hub Alpha",
            position=[400, 400],
            faction="United Humans",
            station_class="Hub",
            model_id="hub_alpha",
            services=["shipyard", "repair", "refuel"],
            ship_inventory=["wasp_combat", "albatross_explorer", "mule_trader"],
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
            ship_inventory=["wasp_combat", "albatross_explorer"],
        )
        self.station_mgr.spawn_station(hub2)

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
        npcs = [
            ("Pirates",     "Small",  "wasp_combat",        100, [900, 300],
             {"hp": 70, "shields": 80}),
            ("Pirates",     "Small",  "wasp_combat",        100, [900, 600],
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
            )
            sid = self.universe.spawn_ship(template, list(pos))
            self.npc_mgr.register_npc(sid, initial_state=NPCBehavior.IDLE)

    # -------------------------------------------------------------- input

    def _handle_input(self):
        for ev in pygame.event.get():
            if ev.type == pygame.QUIT:
                self.running = False
                continue

            # UI da estação consome eventos quando acoplado
            if self.game_state == "docked":
                if self.station_ui.handle_event(ev):
                    continue
                # ESC no menu principal da estação: ignorar (nunca fecha o jogo)
                if ev.type == pygame.KEYDOWN and ev.key == pygame.K_ESCAPE:
                    continue

            if ev.type != pygame.KEYDOWN:
                continue

            # ESC nunca fecha o jogo diretamente — abre/fecha menu de pausa
            if ev.key == pygame.K_ESCAPE:
                if self.game_state == "playing":
                    self.game_state = "paused"
                    self._pause_selection = 0
                elif self.game_state == "paused":
                    self.game_state = "playing"
                continue

            # Navegação do menu de pausa
            if self.game_state == "paused":
                if ev.key == pygame.K_UP:
                    self._pause_selection = (self._pause_selection - 1) % 2
                elif ev.key == pygame.K_DOWN:
                    self._pause_selection = (self._pause_selection + 1) % 2
                elif ev.key in (pygame.K_RETURN, pygame.K_KP_ENTER):
                    if self._pause_selection == 1:
                        self.running = False
                    else:
                        self.game_state = "playing"
                continue

            if self.game_state != "playing":
                continue

            if ev.key == pygame.K_f:
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
        if keys[pygame.K_w]:
            bus.emit("PLAYER_INPUT", {"action": "thrust", "value": 1.0})
            player = self.universe.entities.get(self.player_id)
            if player:
                palette = self.palette_mgr.get_palette(player.faction)
                self.vfx.create_engine_trail(
                    tuple(player.position), player.rotation, palette["accent"][:3]
                )
        if keys[pygame.K_a]:
            bus.emit("PLAYER_INPUT", {"action": "rotate", "value": -1.0})
        if keys[pygame.K_d]:
            bus.emit("PLAYER_INPUT", {"action": "rotate", "value": 1.0})
        if keys[pygame.K_SPACE]:
            bus.emit("PLAYER_INPUT", {"action": "shoot", "value": 1.0})

    # -------------------------------------------------------------- bus listeners

    def _on_docked(self, data):
        station = data["station"]
        self.game_state = "docked"
        player = self.universe.entities.get(self.player_id)
        if player:
            # Parar a nave ao acoplar
            player.velocity = [0.0, 0.0]
        self.station_ui.open(station, player)

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

        # Remove a ship antiga e spawn da nova na mesma posição
        old_pos = list(player.position)
        del self.universe.entities[self.player_id]
        self.player_id = self.universe.spawn_ship(new_template, old_pos)
        new_player = self.universe.entities[self.player_id]

        # Re-aponta managers para a nova ship
        self.player_mgr.ship = new_player
        self.energy_mgr.ship = new_player

        # Atualiza referência na UI
        self.station_ui.player = new_player

    def _on_ship_destroyed(self, data):
        """Se foi a nave do player, dispara fluxo de respawn."""
        if data["ship_id"] == self.player_id:
            self.game_state = "dying"
            self.death_timer = 3.0  # 3s de tela de morte antes de respawn

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
        )
        # Garante que o slot do player não está mais ocupado
        if self.player_id in self.universe.entities:
            del self.universe.entities[self.player_id]

        self.player_id = self.universe.spawn_ship(template, spawn_pos)
        new_player = self.universe.entities[self.player_id]

        self.player_mgr.ship = new_player
        self.energy_mgr.ship = new_player

        self.game_state = "playing"

    # -------------------------------------------------------------- loop

    def run(self):
        while self.running:
            dt = self.clock.tick(60) / 1000.0
            self._handle_input()

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

            self._render()

        pygame.quit()

    def _render(self):
        self.screen.fill(BG_COLOR)
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

        player = self.universe.entities.get(self.player_id)

        # HUD durante gameplay (mostra também em pausa para o fundo ficar visível)
        if self.game_state in ("playing", "paused") and player:
            self.hud.draw(self.screen, player)
            self._draw_combat_hud(player)
            self._draw_docking_prompt()

        if self.game_state == "paused":
            self._draw_pause_menu()
        elif self.game_state == "docked":
            self.station_ui.draw(self.screen)
        elif self.game_state == "dying":
            self._draw_dying_overlay()

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

        options = ["CONTINUAR", "SAIR DO JOGO"]
        for i, label in enumerate(options):
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
        if self.game_state in ("docked", "paused"):
            return  # UI da estação / pausa cuida do próprio help
        lines = [
            "W = thrust   A/D = rotate",
            "ESPAÇO = disparar    F = acoplar",
            "1/2/3 = realocar PIP",
            "ESC = pausar",
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
        print(f"OK — {len(game.universe.entities)} naves, "
              f"{len(game.station_mgr.stations)} estações")
        pygame.quit()
        return
    game.run()


if __name__ == "__main__":
    main()
