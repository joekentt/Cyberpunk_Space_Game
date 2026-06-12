"""
LoadMenuUI — tela de slots de save (carregar E salvar — Bloco F / ADR 012).

Lista N slots fixos (vazios incluídos), cada um com nome do piloto, créditos,
progresso (caçadas) e data. A mesma classe atende dois modos:

  mode="load"  → ENTER num slot preenchido carrega; vazio é inerte.
  mode="save"  → ENTER grava no slot; slot ocupado pede confirmação de
                 sobrescrita antes.

DEL/BACKSPACE sobre um slot preenchido pede confirmação e deleta (ambos os
modos). As entradas são montadas pelo `main_pygame` (que tem o SaveManager) e
passadas em open(entries, mode). Cada entrada é um dict:
    {"slot": int, "empty": True}                                  (slot vazio)
    {"slot": int, "pilot": str, "credits": int,
     "saved_at": float | None, "bounties": int, "completed": bool}

handle_event(ev) retorna:
  ("load", slot)   → carregar o save do slot
  ("save", slot)   → gravar no slot (já confirmado, se precisava)
  ("delete", slot) → deletar o slot (já confirmado)
  "back"           → voltar (menu principal ou pausa, conforme o chamador)
  None             → navegação/sem efeito
"""
import time
import pygame

ROW_H = 64
LIST_Y0 = 150


class LoadMenuUI:
    def __init__(self, width: int, height: int):
        self.W = width
        self.H = height
        self.entries = []
        self.selection = 0
        self.mode = "load"
        # Confirmação pendente: ("overwrite"|"delete", slot) ou None
        self._confirm = None

        self.font_title = pygame.font.SysFont("Consolas", 30, bold=True)
        self.font_row = pygame.font.SysFont("Consolas", 18, bold=True)
        self.font_meta = pygame.font.SysFont("Consolas", 13)
        self.font_small = pygame.font.SysFont("Consolas", 12)

    def open(self, entries, mode: str = "load"):
        self.entries = list(entries)
        self.selection = 0
        self.mode = mode
        self._confirm = None

    # ---- input -------------------------------------------------------

    def handle_event(self, ev):
        # Overlay de confirmação consome tudo primeiro
        if self._confirm is not None:
            return self._handle_confirm(ev)

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
                return self._activate(self.entries[self.selection])
            elif ev.key in (pygame.K_DELETE, pygame.K_BACKSPACE):
                e = self.entries[self.selection]
                if not e.get("empty"):
                    self._confirm = ("delete", e["slot"])
        if ev.type == pygame.MOUSEBUTTONDOWN and ev.button == 1 and self.entries:
            idx = self._row_at(ev.pos)
            if idx is not None:
                self.selection = idx
                return self._activate(self.entries[idx])
        return None

    def _activate(self, entry):
        """ENTER/clique num slot, conforme o modo."""
        if self.mode == "load":
            if entry.get("empty"):
                return None
            return ("load", entry["slot"])
        # mode == "save"
        if entry.get("empty"):
            return ("save", entry["slot"])
        self._confirm = ("overwrite", entry["slot"])
        return None

    def _handle_confirm(self, ev):
        """ENTER/Y confirma; ESC/N cancela."""
        if ev.type != pygame.KEYDOWN:
            return None
        kind, slot = self._confirm
        if ev.key in (pygame.K_RETURN, pygame.K_KP_ENTER, pygame.K_y):
            self._confirm = None
            return ("save" if kind == "overwrite" else "delete", slot)
        if ev.key in (pygame.K_ESCAPE, pygame.K_n):
            self._confirm = None
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
        title_txt = "SALVAR JOGO" if self.mode == "save" else "CARREGAR JOGO"
        title = self.font_title.render(title_txt, True, (0, 220, 255))
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

                if e.get("empty"):
                    color = (120, 135, 150) if not selected else (170, 190, 210)
                    slot_txt = self.font_row.render(
                        f"[{e['slot']}]  — vazio —", True, color)
                    screen.blit(slot_txt, (x0 + 14, row_y + 16))
                    continue

                name_color = (255, 220, 120) if selected else (210, 225, 240)
                slot_txt = self.font_row.render(
                    f"[{e['slot']}]  {e.get('pilot', '?')}", True, name_color)
                screen.blit(slot_txt, (x0 + 14, row_y + 8))

                cr = e.get("credits", 0)
                meta = f"{cr:,} cr".replace(",", ".")
                bounties = e.get("bounties", 0)
                meta += f"    {bounties} caçada{'s' if bounties != 1 else ''}"
                if e.get("completed"):
                    meta += "  ★"
                when = e.get("saved_at")
                if when:
                    meta += "    " + time.strftime("%d/%m/%Y %H:%M", time.localtime(when))
                meta_txt = self.font_meta.render(meta, True, (150, 180, 160))
                screen.blit(meta_txt, (x0 + 14, row_y + 32))

        if self._confirm is not None:
            self._draw_confirm(screen)
            return

        if self.mode == "save":
            hint_txt = "↑↓ navegar    ENTER salvar    DEL apagar    ESC voltar"
        else:
            hint_txt = "↑↓ navegar    ENTER carregar    DEL apagar    ESC voltar"
        hint = self.font_small.render(hint_txt, True, (120, 140, 160))
        screen.blit(hint, hint.get_rect(center=(self.W // 2, self.H - 40)))

    def _draw_confirm(self, screen):
        kind, slot = self._confirm
        overlay = pygame.Surface((self.W, self.H), pygame.SRCALPHA)
        overlay.fill((0, 0, 0, 170))
        screen.blit(overlay, (0, 0))

        if kind == "overwrite":
            msg = f"Sobrescrever o save do slot {slot}?"
            color = (255, 200, 90)
        else:
            msg = f"APAGAR o save do slot {slot}?"
            color = (255, 110, 110)
        box_w, box_h = 460, 120
        bx = self.W // 2 - box_w // 2
        by = self.H // 2 - box_h // 2
        pygame.draw.rect(screen, (16, 24, 36), (bx, by, box_w, box_h))
        pygame.draw.rect(screen, color, (bx, by, box_w, box_h), width=1)

        txt = self.font_row.render(msg, True, color)
        screen.blit(txt, txt.get_rect(center=(self.W // 2, by + 40)))
        hint = self.font_small.render("ENTER/Y confirmar    ESC/N cancelar",
                                      True, (170, 185, 200))
        screen.blit(hint, hint.get_rect(center=(self.W // 2, by + 82)))
