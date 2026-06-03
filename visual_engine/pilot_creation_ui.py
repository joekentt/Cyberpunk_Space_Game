"""
PilotCreationUI — tela de criação de piloto (novo jogo).

Mínimo viável conforme o critério do Ciclo D: capturar o NOME do piloto via
input de texto (KEYDOWN). Trata backspace, limite de caracteres e filtra
caracteres válidos (imprimíveis). ENTER confirma (com nome não-vazio), ESC
cancela e volta ao menu.

handle_event(ev) retorna:
  "confirm" → o jogo deve chamar start_new_game(ui.name)
  "cancel"  → voltar ao menu principal
  None      → evento consumido (digitação/navegação)
"""
import pygame

MAX_NAME = 16
PLACEHOLDER = "Piloto"


class PilotCreationUI:
    def __init__(self, width: int, height: int):
        self.W = width
        self.H = height
        self.name = ""

        self.font_title = pygame.font.SysFont("Consolas", 30, bold=True)
        self.font_label = pygame.font.SysFont("Consolas", 16)
        self.font_input = pygame.font.SysFont("Consolas", 28, bold=True)
        self.font_small = pygame.font.SysFont("Consolas", 12)

        self._caret_timer = 0.0

    def open(self):
        """Reinicia o campo ao abrir."""
        self.name = ""
        self._caret_timer = 0.0

    # ---- input -------------------------------------------------------

    def handle_event(self, ev):
        if ev.type != pygame.KEYDOWN:
            return None

        if ev.key == pygame.K_ESCAPE:
            return "cancel"
        if ev.key in (pygame.K_RETURN, pygame.K_KP_ENTER):
            # Nome vazio → usa o placeholder, mas sempre confirma.
            if not self.name.strip():
                self.name = PLACEHOLDER
            return "confirm"
        if ev.key == pygame.K_BACKSPACE:
            self.name = self.name[:-1]
            return None

        # Caractere imprimível (ev.unicode já respeita shift/layout).
        # Aceita letras, dígitos, espaço e pontuação; ignora controles.
        ch = ev.unicode
        if ch and ch.isprintable() and len(self.name) < MAX_NAME:
            self.name += ch
        return None

    def update(self, dt: float):
        self._caret_timer = (self._caret_timer + dt) % 1.0

    # ---- render ------------------------------------------------------

    def draw(self, screen):
        title = self.font_title.render("CRIAR PILOTO", True, (0, 220, 255))
        screen.blit(title, title.get_rect(center=(self.W // 2, self.H // 4)))

        label = self.font_label.render("Nome do piloto:", True, (170, 190, 210))
        screen.blit(label, label.get_rect(center=(self.W // 2, self.H // 2 - 56)))

        # Caixa de input
        box_w, box_h = 360, 52
        box = pygame.Rect(self.W // 2 - box_w // 2, self.H // 2 - box_h // 2,
                          box_w, box_h)
        pygame.draw.rect(screen, (14, 22, 34), box)
        pygame.draw.rect(screen, (0, 200, 240), box, width=1)

        shown = self.name if self.name else ""
        caret = "_" if self._caret_timer < 0.5 else " "
        text = self.font_input.render(shown + caret, True, (255, 235, 150))
        screen.blit(text, text.get_rect(midleft=(box.x + 14, box.centery)))

        if not self.name:
            ph = self.font_label.render(f"(vazio = \"{PLACEHOLDER}\")", True, (90, 110, 130))
            screen.blit(ph, ph.get_rect(center=(self.W // 2, self.H // 2 + 44)))

        hint = self.font_small.render(
            "Digite o nome    ENTER confirmar    ESC cancelar",
            True, (120, 140, 160))
        screen.blit(hint, hint.get_rect(center=(self.W // 2, self.H - 40)))
