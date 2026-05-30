"""
KeybindsUI — tela de remapeamento de teclas, acessível pelo menu de pausa.

Fluxo:
  ↑ ↓        navega entre as ações
  ENTER      entra em modo "aguardando tecla" para a ação selecionada
  (tecla)    enquanto aguarda, a próxima tecla pressionada vira o novo bind
  ESC        sai da tela (ou cancela o rebind, se estiver aguardando)
  BACKSPACE  restaura todos os binds para o padrão
  clique     seleciona a ação sob o cursor e já entra em "aguardando tecla"

Detecta conflitos (duas ações na mesma tecla) e avisa, destacando as
linhas conflitantes em vermelho.

handle_event(ev) retorna:
  "close"  → o jogo deve voltar ao menu de pausa
  None     → evento consumido por esta tela
"""
import pygame


# Geometria da lista (compartilhada entre draw e detecção de clique)
LIST_X = 80
LIST_W = 560
ROW_H = 34
LIST_Y0 = 150


class KeybindsUI:
    def __init__(self, width: int, height: int, input_cfg, on_change=None):
        self.W = width
        self.H = height
        self.input_cfg = input_cfg
        self.on_change = on_change  # callback chamado quando um bind muda

        self.selection = 0
        self.waiting = False        # True = esperando nova tecla para o rebind
        self.message = ""

        self.font_title = pygame.font.SysFont("Consolas", 26, bold=True)
        self.font_row = pygame.font.SysFont("Consolas", 16)
        self.font_small = pygame.font.SysFont("Consolas", 12)

    def open(self):
        """Reinicia o estado ao abrir a tela."""
        self.selection = 0
        self.waiting = False
        self.message = ""

    # ---- input -------------------------------------------------------

    def handle_event(self, ev):
        actions = self.input_cfg.ACTIONS

        # Modo "aguardando nova tecla"
        if self.waiting:
            if ev.type == pygame.KEYDOWN:
                if ev.key == pygame.K_ESCAPE:
                    self.waiting = False
                    self.message = "Rebind cancelado."
                else:
                    self._apply_rebind(actions[self.selection], ev.key)
            return None

        if ev.type == pygame.KEYDOWN:
            if ev.key == pygame.K_ESCAPE:
                return "close"
            elif ev.key == pygame.K_UP:
                self.selection = (self.selection - 1) % len(actions)
            elif ev.key == pygame.K_DOWN:
                self.selection = (self.selection + 1) % len(actions)
            elif ev.key in (pygame.K_RETURN, pygame.K_KP_ENTER):
                self.waiting = True
                self.message = "Pressione a nova tecla (ESC cancela)…"
            elif ev.key == pygame.K_BACKSPACE:
                self.input_cfg.reset_to_defaults()
                self.input_cfg.save()
                if self.on_change:
                    self.on_change()
                self.message = "Teclas restauradas para o padrão."
            return None

        if ev.type == pygame.MOUSEBUTTONDOWN and ev.button == 1:
            idx = self._row_at(ev.pos)
            if idx is not None:
                self.selection = idx
                self.waiting = True
                self.message = "Pressione a nova tecla (ESC cancela)…"
            return None

        return None

    def _apply_rebind(self, action, key_code):
        key_name = pygame.key.name(key_code)
        self.input_cfg.set(action, key_name)
        self.input_cfg.save()
        if self.on_change:
            self.on_change()
        self.waiting = False

        conflicts = self.input_cfg.conflicts()
        if key_name in conflicts:
            others = [self.input_cfg.label(a) for a in conflicts[key_name] if a != action]
            self.message = f"⚠ '{key_name.upper()}' em conflito com: {', '.join(others)}"
        else:
            self.message = f"{self.input_cfg.label(action)} → {key_name.upper()}"

    def _row_at(self, pos):
        """Índice da linha sob a posição do mouse, ou None."""
        mx, my = pos
        if not (LIST_X <= mx <= LIST_X + LIST_W):
            return None
        for i in range(len(self.input_cfg.ACTIONS)):
            row_y = LIST_Y0 + i * ROW_H
            if row_y <= my <= row_y + ROW_H:
                return i
        return None

    # ---- render ------------------------------------------------------

    def draw(self, screen):
        overlay = pygame.Surface((self.W, self.H), pygame.SRCALPHA)
        overlay.fill((5, 8, 18, 235))
        screen.blit(overlay, (0, 0))
        pygame.draw.rect(screen, (0, 150, 200),
                         (20, 20, self.W - 40, self.H - 40), width=1)

        title = self.font_title.render("CONFIGURAR TECLAS", True, (0, 220, 255))
        screen.blit(title, (LIST_X, 50))
        sub = self.font_small.render(
            "↑↓ navegar   ENTER rebind   ESC voltar   BACKSPACE restaurar padrão",
            True, (140, 160, 180),
        )
        screen.blit(sub, (LIST_X, 90))

        conflicts = self.input_cfg.conflicts()
        actions = self.input_cfg.ACTIONS
        for i, action in enumerate(actions):
            row_y = LIST_Y0 + i * ROW_H
            selected = (i == self.selection)
            key_name = self.input_cfg.get(action)
            in_conflict = key_name in conflicts

            if selected:
                pygame.draw.rect(screen, (30, 60, 90),
                                 (LIST_X, row_y, LIST_W, ROW_H - 4))
                pygame.draw.rect(screen, (0, 200, 240),
                                 (LIST_X, row_y, LIST_W, ROW_H - 4), width=1)

            label_color = (255, 220, 120) if selected else (200, 220, 240)
            label = self.font_row.render(self.input_cfg.label(action), True, label_color)
            screen.blit(label, (LIST_X + 14, row_y + 6))

            # Tecla atual (ou "<pressione…>" se aguardando neste item)
            if selected and self.waiting:
                key_text = "< pressione… >"
                key_color = (255, 230, 120)
            else:
                key_text = f"[ {key_name.upper()} ]"
                key_color = (255, 90, 80) if in_conflict else (140, 230, 160)
            kt = self.font_row.render(key_text, True, key_color)
            screen.blit(kt, (LIST_X + LIST_W - kt.get_width() - 14, row_y + 6))

        # Mensagem de status / aviso de conflito
        if self.message:
            color = (255, 120, 90) if self.message.startswith("⚠") else (255, 220, 120)
            msg = self.font_row.render(self.message, True, color)
            screen.blit(msg, msg.get_rect(center=(self.W // 2, self.H - 70)))

        if conflicts:
            warn = self.font_small.render(
                "Há teclas em conflito (em vermelho). Reatribua para resolver.",
                True, (255, 120, 90),
            )
            screen.blit(warn, warn.get_rect(center=(self.W // 2, self.H - 48)))
