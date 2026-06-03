"""
MainMenuUI — menu principal, primeira tela do jogo.

Segue o padrão das outras UIs (StationUI, KeybindsUI): navegação por teclado
↑↓/ENTER e métodos handle_event(ev) / draw(screen). O mundo NÃO é carregado
até o jogador escolher "NOVO JOGO" ou "CARREGAR JOGO".

handle_event(ev) retorna uma string de ação quando o jogador confirma:
  "new_game" | "load" | "keybinds" | "quit"
ou None se o evento foi apenas navegação/sem efeito.

A opção "CARREGAR JOGO" só aparece quando há saves — passe `has_saves` em open().
"""
import pygame


class MainMenuUI:
    def __init__(self, width: int, height: int):
        self.W = width
        self.H = height
        self.selection = 0
        self.options = []   # lista de (rótulo, ação)

        self.font_title = pygame.font.SysFont("Consolas", 44, bold=True)
        self.font_sub = pygame.font.SysFont("Consolas", 16)
        self.font_opt = pygame.font.SysFont("Consolas", 22, bold=True)
        self.font_small = pygame.font.SysFont("Consolas", 12)

    def open(self, has_saves: bool):
        """(Re)constrói as opções. 'CARREGAR JOGO' some quando não há saves."""
        opts = [("NOVO JOGO", "new_game")]
        if has_saves:
            opts.append(("CARREGAR JOGO", "load"))
        opts.append(("CONFIGURAR TECLAS", "keybinds"))
        opts.append(("SAIR", "quit"))
        self.options = opts
        self.selection = 0

    # ---- input -------------------------------------------------------

    def handle_event(self, ev):
        if ev.type == pygame.KEYDOWN:
            if ev.key == pygame.K_UP:
                self.selection = (self.selection - 1) % len(self.options)
            elif ev.key == pygame.K_DOWN:
                self.selection = (self.selection + 1) % len(self.options)
            elif ev.key in (pygame.K_RETURN, pygame.K_KP_ENTER):
                return self.options[self.selection][1]
        if ev.type == pygame.MOUSEBUTTONDOWN and ev.button == 1:
            idx = self._row_at(ev.pos)
            if idx is not None:
                self.selection = idx
                return self.options[idx][1]
        return None

    def _row_at(self, pos):
        mx, my = pos
        base_y = self.H // 2 - 30
        for i in range(len(self.options)):
            row_y = base_y + i * 44
            if abs(my - row_y) <= 20 and abs(mx - self.W // 2) <= 220:
                return i
        return None

    # ---- render ------------------------------------------------------

    def draw(self, screen):
        # Título com leve sombra de neon
        title = "CYBERPUNK SPACE RPG"
        shadow = self.font_title.render(title, True, (0, 80, 110))
        screen.blit(shadow, shadow.get_rect(center=(self.W // 2 + 3, self.H // 4 + 3)))
        main = self.font_title.render(title, True, (0, 220, 255))
        screen.blit(main, main.get_rect(center=(self.W // 2, self.H // 4)))

        sub = self.font_sub.render("um RPG espacial de fronteira", True, (150, 170, 200))
        screen.blit(sub, sub.get_rect(center=(self.W // 2, self.H // 4 + 40)))

        base_y = self.H // 2 - 30
        for i, (label, _) in enumerate(self.options):
            row_y = base_y + i * 44
            selected = (i == self.selection)
            if selected:
                w = 300
                pygame.draw.rect(screen, (20, 45, 70),
                                 (self.W // 2 - w // 2, row_y - 18, w, 36))
                pygame.draw.rect(screen, (0, 200, 240),
                                 (self.W // 2 - w // 2, row_y - 18, w, 36), width=1)
            color = (255, 220, 120) if selected else (200, 220, 240)
            prefix = "▸ " if selected else ""
            text = self.font_opt.render(prefix + label, True, color)
            screen.blit(text, text.get_rect(center=(self.W // 2, row_y)))

        hint = self.font_small.render(
            "↑↓ navegar    ENTER selecionar", True, (120, 140, 160))
        screen.blit(hint, hint.get_rect(center=(self.W // 2, self.H - 40)))
