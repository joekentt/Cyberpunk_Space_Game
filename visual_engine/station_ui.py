"""
StationUI — overlay renderizado quando o jogador está atracado.

Telas:
  - MAIN        Menu principal (Mercado, Reparar, Desacoplar)
  - SHIPYARD    Mercado de naves (lista navegável + compra)
  - REPAIRED    Confirmação de reparo

Controles dentro da UI:
  - SETA CIMA/BAIXO    navegar listas/menus
  - ENTER              confirmar
  - ESC / BACK         voltar para a tela anterior
  - F                  desacoplar (quando no menu principal)
"""
import pygame
import os
import json
from core.event_bus import bus
from core.balance import balance
from systems.combat_manager import CombatManager


class StationUI:
    SCREEN_MAIN = "main"
    SCREEN_SHIPYARD = "shipyard"
    SCREEN_REPAIRED = "repaired"
    SCREEN_MISSIONS = "missions"

    def __init__(self, width: int, height: int, ships_data_path: str):
        self.W = width
        self.H = height

        # Estado
        self.screen = self.SCREEN_MAIN
        self.menu_selection = 0           # índice do menu atual
        self.shipyard_selection = 0       # índice da nave selecionada
        self.missions_selection = 0       # índice da missão selecionada
        self.available_missions = []      # missões disponíveis nesta estação
        self.station = None               # Station atual
        self.player = None                # Ship do jogador
        self.hidden_poi_count = 0         # POIs ainda ocultos (cartografia)
        self.message: str = ""            # mensagem efêmera (sucesso/erro)
        self.message_timer = 0.0

        # Carrega catálogo de naves uma vez
        with open(ships_data_path, "r") as f:
            self.ships_catalog = json.load(f)["ships"]

        # Fontes
        self.font_title = pygame.font.SysFont("Consolas", 28, bold=True)
        self.font_section = pygame.font.SysFont("Consolas", 18, bold=True)
        self.font_body = pygame.font.SysFont("Consolas", 14)
        self.font_small = pygame.font.SysFont("Consolas", 12)

    # ---- Lifecycle -----------------------------------------------------

    def open(self, station, player, available_missions=None,
             hidden_poi_count: int = 0):
        self.station = station
        self.player = player
        self.screen = self.SCREEN_MAIN
        self.menu_selection = 0
        self.shipyard_selection = 0
        self.missions_selection = 0
        self.available_missions = list(available_missions or [])
        self.hidden_poi_count = int(hidden_poi_count)
        self.message = ""

    def close(self):
        self.station = None
        self.player = None

    def show_message(self, text: str, duration: float = 2.5):
        self.message = text
        self.message_timer = duration

    def update(self, dt: float):
        if self.message_timer > 0:
            self.message_timer -= dt
            if self.message_timer <= 0:
                self.message = ""

    # ---- Input ---------------------------------------------------------

    def handle_event(self, ev) -> bool:
        """
        Processa um evento pygame. Retorna True se a UI lidou com ele
        (não deve repassar para o jogo).
        """
        if ev.type != pygame.KEYDOWN:
            return False

        if self.screen == self.SCREEN_MAIN:
            return self._handle_main(ev)
        elif self.screen == self.SCREEN_SHIPYARD:
            return self._handle_shipyard(ev)
        elif self.screen == self.SCREEN_MISSIONS:
            return self._handle_missions(ev)
        elif self.screen == self.SCREEN_REPAIRED:
            self.screen = self.SCREEN_MAIN
            return True
        return False

    def _handle_main(self, ev) -> bool:
        options = self._main_options()
        if ev.key == pygame.K_UP:
            self.menu_selection = (self.menu_selection - 1) % len(options)
            return True
        if ev.key == pygame.K_DOWN:
            self.menu_selection = (self.menu_selection + 1) % len(options)
            return True
        if ev.key in (pygame.K_RETURN, pygame.K_KP_ENTER):
            self._execute_main_option(options[self.menu_selection])
            return True
        if ev.key == pygame.K_f:
            # Desacopla diretamente do menu principal
            bus.emit("PLAYER_INPUT", {"action": "dock_toggle"})
            return True
        if ev.key == pygame.K_ESCAPE:
            # Consome ESC no SCREEN_MAIN: nunca propaga para fechar o jogo
            return True
        return False

    def _handle_shipyard(self, ev) -> bool:
        purchasable = self._shipyard_ships()
        if ev.key == pygame.K_UP:
            self.shipyard_selection = max(0, self.shipyard_selection - 1)
            return True
        if ev.key == pygame.K_DOWN:
            self.shipyard_selection = min(len(purchasable) - 1, self.shipyard_selection + 1)
            return True
        if ev.key in (pygame.K_RETURN, pygame.K_KP_ENTER):
            if purchasable:
                self._buy_ship(purchasable[self.shipyard_selection])
            return True
        if ev.key == pygame.K_ESCAPE:
            self.screen = self.SCREEN_MAIN
            return True
        return False

    def _handle_missions(self, ev) -> bool:
        if ev.key == pygame.K_UP:
            self.missions_selection = max(0, self.missions_selection - 1)
            return True
        if ev.key == pygame.K_DOWN:
            self.missions_selection = min(
                len(self.available_missions) - 1, self.missions_selection + 1
            )
            return True
        if ev.key in (pygame.K_RETURN, pygame.K_KP_ENTER):
            if self.available_missions:
                m = self.available_missions[self.missions_selection]
                bus.emit("MISSION_ACCEPT_REQUEST", {"mission_id": m.id})
                self.available_missions.pop(self.missions_selection)
                self.missions_selection = max(0, self.missions_selection - 1)
                self.show_message(f"Missão aceita!")
            return True
        if ev.key == pygame.K_ESCAPE:
            self.screen = self.SCREEN_MAIN
            return True
        return False

    # ---- Logic ---------------------------------------------------------

    def _main_options(self):
        opts = []
        if "shipyard" in self.station.services:
            opts.append(("MERCADO DE NAVES", "shipyard"))
        if "repair" in self.station.services:
            opts.append(("REPARAR NAVE (grátis)", "repair"))
        mission_count = len(self.available_missions)
        label = f"MISSÕES ({mission_count})" if mission_count else "MISSÕES"
        opts.append((label, "missions"))
        price = balance.exploration["cartography_price"]
        opts.append((f"CARTOGRAFIA ({price:,} cr)".replace(",", "."),
                     "cartography"))
        opts.append(("DESACOPLAR", "undock"))
        return opts

    def _execute_main_option(self, opt):
        _, key = opt
        if key == "shipyard":
            self.screen = self.SCREEN_SHIPYARD
            self.shipyard_selection = 0
        elif key == "repair":
            self.player.current_hp = self.player.max_hp
            self.player.current_shields = self.player.max_shields
            self.screen = self.SCREEN_REPAIRED
            self.show_message("Casco e escudos restaurados.")
        elif key == "missions":
            self.screen = self.SCREEN_MISSIONS
            self.missions_selection = 0
        elif key == "cartography":
            self._buy_cartography()
        elif key == "undock":
            bus.emit("PLAYER_INPUT", {"action": "dock_toggle"})

    def _shipyard_ships(self):
        """Lista de naves disponíveis NESTA estação (filtra do catálogo)."""
        if not self.station.ship_inventory:
            # Default: todas as naves não-starter
            return [s for s in self.ships_catalog
                    if not s.get("starting_ship", False)]
        # Filtra pelas IDs no inventário da estação
        ids = set(self.station.ship_inventory)
        return [s for s in self.ships_catalog if s["id"] in ids]

    def _buy_ship(self, ship_data: dict):
        price = ship_data.get("base_price", 0)
        if self.player.credits < price:
            self.show_message(f"Créditos insuficientes ({self.player.credits}/{price})")
            return
        if self.player.model_id == ship_data.get("model_id"):
            self.show_message(f"Você já pilota uma {ship_data['name']}")
            return

        # Troca de nave: debita créditos, emite evento para o main_pygame
        # trocar a Ship do player.
        self.player.credits -= price
        bus.emit("SHIP_PURCHASED", {
            "ship_data": ship_data,
            "buyer_id": self.player.id,
        })
        self.show_message(f"Nave adquirida: {ship_data['name']}")

    def _buy_cartography(self):
        """
        Compra dados de cartografia (ADR 011): debita créditos (fonte única,
        mesmo padrão do _buy_ship) e emite CARTOGRAPHY_PURCHASED para o
        ExplorationManager revelar os POIs.
        """
        price = balance.exploration["cartography_price"]
        count = balance.exploration["cartography_reveal_count"]
        if self.hidden_poi_count <= 0:
            self.show_message("Sem novos dados de cartografia disponíveis")
            return
        if self.player.credits < price:
            self.show_message(f"Créditos insuficientes ({self.player.credits}/{price})")
            return

        self.player.credits -= price
        revealed = min(count, self.hidden_poi_count)
        self.hidden_poi_count -= revealed
        bus.emit("CARTOGRAPHY_PURCHASED", {
            "count": count,
            "buyer_id": self.player.id,
        })
        self.show_message(
            f"Cartografia adquirida: {revealed} localização(ões) revelada(s)")

    # ---- Render --------------------------------------------------------

    def draw(self, screen: pygame.Surface):
        # Fundo escuro semi-transparente
        overlay = pygame.Surface((self.W, self.H), pygame.SRCALPHA)
        overlay.fill((5, 8, 18, 230))
        screen.blit(overlay, (0, 0))

        # Borda decorativa
        pygame.draw.rect(screen, (0, 150, 200),
                         (20, 20, self.W - 40, self.H - 40), width=1)

        # Cabeçalho
        title = self.font_title.render(
            f"⌂ {self.station.name}",
            True, (0, 220, 255)
        )
        screen.blit(title, (40, 36))
        subtitle = self.font_body.render(
            f"Facção: {self.station.faction}   |   Serviços: {', '.join(self.station.services)}",
            True, (180, 200, 220)
        )
        screen.blit(subtitle, (40, 70))

        # Player info à direita
        if self.player:
            cred_text = self.font_section.render(
                f"⚙ {self.player.credits:,} cr".replace(",", "."),
                True, (255, 200, 60)
            )
            screen.blit(cred_text, (self.W - cred_text.get_width() - 40, 36))
            ship_text = self.font_body.render(
                f"Pilotando: {self.player.name} ({self.player.ship_class})",
                True, (180, 200, 220)
            )
            screen.blit(ship_text, (self.W - ship_text.get_width() - 40, 70))

        # Linha divisória
        pygame.draw.line(screen, (60, 100, 130),
                         (40, 100), (self.W - 40, 100), width=1)

        # Tela
        if self.screen == self.SCREEN_MAIN:
            self._draw_main(screen)
        elif self.screen == self.SCREEN_SHIPYARD:
            self._draw_shipyard(screen)
        elif self.screen == self.SCREEN_MISSIONS:
            self._draw_missions(screen)

        # Mensagem flutuante (centro inferior)
        if self.message:
            msg_surf = self.font_section.render(self.message, True, (255, 220, 120))
            mrect = msg_surf.get_rect(center=(self.W // 2, self.H - 60))
            bg = pygame.Surface((mrect.w + 20, mrect.h + 10), pygame.SRCALPHA)
            bg.fill((0, 0, 0, 180))
            screen.blit(bg, (mrect.x - 10, mrect.y - 5))
            screen.blit(msg_surf, mrect)

        # Help no rodapé
        help_text = self._help_text()
        ht = self.font_small.render(help_text, True, (120, 140, 160))
        screen.blit(ht, (self.W // 2 - ht.get_width() // 2, self.H - 28))

    def _help_text(self) -> str:
        if self.screen == self.SCREEN_MAIN:
            return "↑↓ navegar   ENTER selecionar   F desacoplar"
        elif self.screen == self.SCREEN_SHIPYARD:
            return "↑↓ navegar   ENTER comprar   ESC voltar"
        elif self.screen == self.SCREEN_MISSIONS:
            return "↑↓ navegar   ENTER aceitar missão   ESC voltar"
        return ""

    def _draw_main(self, screen):
        y = 140
        options = self._main_options()
        title = self.font_section.render("MENU", True, (0, 200, 240))
        screen.blit(title, (40, y))
        y += 36
        for i, (label, _) in enumerate(options):
            color = (255, 220, 120) if i == self.menu_selection else (200, 220, 240)
            prefix = "▸ " if i == self.menu_selection else "  "
            text = self.font_section.render(prefix + label, True, color)
            screen.blit(text, (60, y))
            y += 32

    def _draw_shipyard(self, screen):
        y = 130
        title = self.font_section.render("MERCADO DE NAVES", True, (0, 200, 240))
        screen.blit(title, (40, y))
        y += 30

        ships = self._shipyard_ships()
        if not ships:
            no = self.font_body.render(
                "Esta estação não tem naves disponíveis no momento.",
                True, (180, 180, 200)
            )
            screen.blit(no, (40, y))
            return

        # Lista de naves
        list_x = 40
        list_w = 380
        for i, sd in enumerate(ships):
            row_y = y + i * 60
            selected = (i == self.shipyard_selection)
            bg_color = (30, 60, 90) if selected else (20, 25, 40)
            pygame.draw.rect(screen, bg_color, (list_x, row_y, list_w, 54))
            if selected:
                pygame.draw.rect(screen, (0, 200, 240),
                                 (list_x, row_y, list_w, 54), width=1)

            # Nome + class
            name = self.font_section.render(sd["name"], True, (220, 240, 255))
            screen.blit(name, (list_x + 12, row_y + 4))
            role = self.font_small.render(
                f"{sd['role']} · {sd['class']}",
                True, (140, 170, 200)
            )
            screen.blit(role, (list_x + 12, row_y + 30))

            # Preço (lado direito)
            price = sd.get("base_price", 0)
            ok = self.player.credits >= price
            price_color = (120, 230, 120) if ok else (255, 100, 80)
            price_text = self.font_body.render(
                f"{price:,} cr".replace(",", ".") if price > 0 else "GRÁTIS",
                True, price_color
            )
            screen.blit(price_text, (list_x + list_w - price_text.get_width() - 12,
                                     row_y + 6))

        # Detalhes da nave selecionada (lado direito)
        if 0 <= self.shipyard_selection < len(ships):
            self._draw_ship_details(screen, ships[self.shipyard_selection],
                                    x=list_x + list_w + 30, y=y)

    def _draw_ship_details(self, screen, sd, x, y):
        # Caixa
        w = self.W - x - 40
        h = 380
        pygame.draw.rect(screen, (15, 20, 35), (x, y, w, h))
        pygame.draw.rect(screen, (0, 150, 200), (x, y, w, h), width=1)

        # Header
        head = self.font_section.render(sd["name"], True, (0, 220, 255))
        screen.blit(head, (x + 16, y + 10))
        role = self.font_small.render(
            f"{sd['role'].upper()} · TIER {sd.get('tier', 1)} · {sd['class']}",
            True, (140, 170, 200)
        )
        screen.blit(role, (x + 16, y + 40))

        # Linha
        pygame.draw.line(screen, (60, 100, 130),
                         (x + 16, y + 64), (x + w - 16, y + 64), width=1)

        # Descrição (quebrada em linhas)
        desc = sd.get("description", "")
        desc_y = y + 76
        words = desc.split()
        line = ""
        max_w = w - 32
        lines = []
        for word in words:
            test = (line + " " + word).strip()
            if self.font_small.size(test)[0] <= max_w:
                line = test
            else:
                lines.append(line)
                line = word
        if line:
            lines.append(line)
        for ln in lines[:5]:
            txt = self.font_small.render(ln, True, (180, 200, 220))
            screen.blit(txt, (x + 16, desc_y))
            desc_y += 16

        # Stats
        sy = desc_y + 12
        stats = sd["base_stats"]
        hp = sd.get("hardpoints", {})
        hp_str_parts = []
        if hp.get("weapon_small", 0): hp_str_parts.append(f"{hp['weapon_small']}S")
        if hp.get("weapon_medium", 0): hp_str_parts.append(f"{hp['weapon_medium']}M")
        if hp.get("weapon_large", 0): hp_str_parts.append(f"{hp['weapon_large']}L")
        if hp.get("utility", 0): hp_str_parts.append(f"{hp['utility']}U")
        hp_str = " + ".join(hp_str_parts) if hp_str_parts else "—"

        # Poder de fogo derivado dos hardpoints de arma. Usa o MESMO helper do
        # CombatManager (fonte única da fórmula) para nunca dessincronizar.
        firepower = CombatManager.firepower_from_hardpoints(hp)

        rows = [
            ("CASCO", f"{stats.get('hull_hp', '—')} HP"),
            ("ESCUDOS", f"{stats.get('shields_max', '—')}"),
            ("ENERGIA", f"{stats.get('energy_capacity', '—')}"),
            ("MASSA", f"{stats.get('mass', '—')} t"),
            ("CARGA", f"{stats.get('cargo_capacity', '—')} m³"),
            ("HARDPOINTS", hp_str),
            ("PODER DE FOGO", f"x{firepower:.1f} dano/tiro"),
        ]
        for k, v in rows:
            l = self.font_small.render(k, True, (120, 140, 160))
            screen.blit(l, (x + 16, sy))
            highlight = (255, 200, 80) if k == "PODER DE FOGO" else (220, 230, 240)
            r = self.font_body.render(str(v), True, highlight)
            screen.blit(r, (x + 130, sy))
            sy += 20

        note = self.font_small.render(
            "Mais hardpoints de arma = mais poder de fogo.",
            True, (140, 170, 200),
        )
        screen.blit(note, (x + 16, sy + 2))
        sy += 18

        # Preço
        price = sd.get("base_price", 0)
        ok = self.player.credits >= price
        price_color = (120, 230, 120) if ok else (255, 100, 80)
        price_text = self.font_section.render(
            f"{price:,} cr".replace(",", "."),
            True, price_color
        )
        screen.blit(price_text, (x + 16, sy + 12))
        if not ok:
            need = self.font_small.render(
                f"Faltam {(price - self.player.credits):,} cr".replace(",", "."),
                True, (255, 80, 60)
            )
            screen.blit(need, (x + 16, sy + 40))

    def _draw_missions(self, screen):
        y = 130
        header = self.font_section.render("MISSÕES DISPONÍVEIS", True, (0, 200, 240))
        screen.blit(header, (40, y))
        y += 36

        if not self.available_missions:
            no = self.font_body.render(
                "Nenhuma missão disponível nesta estação.", True, (180, 180, 200)
            )
            screen.blit(no, (40, y))
            return

        row_h = 76
        for i, m in enumerate(self.available_missions):
            row_y = y + i * row_h
            selected = (i == self.missions_selection)
            bg_col = (30, 60, 90) if selected else (20, 25, 40)
            pygame.draw.rect(screen, bg_col, (40, row_y, self.W - 80, row_h - 6))
            if selected:
                pygame.draw.rect(screen, (0, 200, 240),
                                 (40, row_y, self.W - 80, row_h - 6), width=1)

            # Título da missão
            t_surf = self.font_section.render(m.title, True, (220, 240, 255))
            screen.blit(t_surf, (56, row_y + 6))

            # Descrição (truncada)
            desc = m.description
            if len(desc) > 90:
                desc = desc[:87] + "..."
            d_surf = self.font_small.render(desc, True, (140, 170, 200))
            screen.blit(d_surf, (56, row_y + 30))

            # Objetivo (lado esquerdo, linha inferior)
            kill_obj = next(
                (o for o in m.objectives if o.get("type") == "KILL"), None
            )
            if kill_obj:
                obj_str = (f"Eliminar {kill_obj.get('count', 1)}"
                           f" {kill_obj.get('target_faction', 'inimigos')}")
                obj_surf = self.font_small.render(obj_str, True, (255, 160, 60))
                screen.blit(obj_surf, (56, row_y + 50))

            # Recompensa (canto direito)
            reward_surf = self.font_body.render(
                f"+{m.reward_credits:,} cr".replace(",", "."),
                True, (120, 230, 120)
            )
            screen.blit(reward_surf,
                        (self.W - reward_surf.get_width() - 56, row_y + 6))
