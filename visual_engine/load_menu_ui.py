"""
LoadMenuUI — tela de carregar jogo.

Lista os saves disponíveis (preparada para multi-slot, embora o Ciclo C use
slot único). Cada entrada mostra nome do piloto, créditos e, se disponível no
payload, a data do save. Navegação por teclado no padrão das outras UIs.

As entradas são montadas pelo `main_pygame` (que tem o SaveManager) e passadas
em open(entries). Cada entrada é um dict:
    {"slot": int, "pilot": str, "credits": int, "saved_at": float | None}

handle_event(ev) retorna:
  ("load", slot) → carregar o save do slot
  "back"         → voltar ao menu principal
  None           → navegação/sem efeito
"""
import time
import pygame

ROW_H = 56
LIST_Y0 = 150


class LoadMenuUI:
    def __init__(self, width: int, height: int):
        self.W = width
        self.H = height
        self.entries = []
        self.selection = 0

        self.font_title = pygame.font.SysFont("Consolas", 30, bold=True)
        self.font_row = pygame.font.SysFont("Consolas", 18, bold=True)
        self.font_meta = pygame.font.SysFont("Consolas", 13)
        self.font_small = pygame.font.SysFont("Consolas", 12)

    def open(self, entries):
        self.entries = list(entries)
        self.selection = 0

    # ---- input -------------------------------------------------------

    def handle_event(self, ev):
        if ev.type == pygame.KEYDOWN:
            if ev.key == pygame.K_ESCAPE:
                return "back"
            if not self.entries:
                return None
            if ev.key == pygame.K_UP:
                self.selection = (self.selection - 1) % len(self.entries)
            elif ev.key == pygame.K_DOWN:
                self.selection = (self.selection + 1) % len(self.entries)
            elif ev.key in (pygame.K_RETURN, pygame.K_KP_ENTER):
                return ("load", self.entries[self.selection]["slot"])
        if ev.type == pygame.MOUSEBUTTONDOWN and ev.button == 1 and self.entries:
            idx = self._row_at(ev.pos)
            if idx is not None:
                self.selection = idx
                return ("load", self.entries[idx]["slot"])
        return None

    def _row_at(self, pos):
        mx, my = pos
        x0 = self.W // 2 - 280
        if not (x0 <= mx <= x0 + 560):
            return None
        for i in range(len(self.entries)):
            row_y = LIST_Y0 + i * ROW_H
            if row_y <= my <= row_y + ROW_H - 8:
                return i
        return None

    # ---- render ------------------------------------------------------

    def draw(self, screen):
        title = self.font_title.render("CARREGAR JOGO", True, (0, 220, 255))
        screen.blit(title, title.get_rect(center=(self.W // 2, 80)))

        if not self.entries:
            empty = self.font_row.render("Nenhum save encontrado.", True, (180, 160, 160))
            screen.blit(empty, empty.get_rect(center=(self.W // 2, self.H // 2)))
        else:
            x0 = self.W // 2 - 280
            for i, e in enumerate(self.entries):
                row_y = LIST_Y0 + i * ROW_H
                selected = (i == self.selection)
                if selected:
                    pygame.draw.rect(screen, (20, 45, 70), (x0, row_y, 560, ROW_H - 8))
                    pygame.draw.rect(screen, (0, 200, 240), (x0, row_y, 560, ROW_H - 8),
                                     width=1)
                name_color = (255, 220, 120) if selected else (210, 225, 240)
                slot_txt = self.font_row.render(
                    f"[{e['slot']}]  {e.get('pilot', '?')}", True, name_color)
                screen.blit(slot_txt, (x0 + 14, row_y + 8))

                cr = e.get("credits", 0)
                meta = f"{cr:,} cr".replace(",", ".")
                when = e.get("saved_at")
                if when:
                    meta += "    " + time.strftime("%d/%m/%Y %H:%M", time.localtime(when))
                meta_txt = self.font_meta.render(meta, True, (150, 180, 160))
                screen.blit(meta_txt, (x0 + 14, row_y + 30))

        hint = self.font_small.render(
            "↑↓ navegar    ENTER carregar    ESC voltar", True, (120, 140, 160))
        screen.blit(hint, hint.get_rect(center=(self.W // 2, self.H - 40)))
