"""
EndgameUI — tela de epílogo exibida ao completar a condição de vitória.

Exibe texto narrativo e duas opções:
  CONTINUAR  — fecha a tela e volta ao jogo (pode continuar jogando)
  VOLTAR AO MENU — vai para o menu principal

Padrão: open(pilot_name), handle_event(ev) → "continue"|"menu"|None, draw(screen).
"""
import pygame


EPILOGUE = [
    "As lideranças piratas que controlavam as rotas",
    "comerciais do setor foram neutralizadas.",
    "",
    "O tráfego voltou a fluir. As estações respiram.",
    "Por quanto tempo? Ninguém sabe.",
    "",
    "Mas por hoje, foi suficiente.",
]


class EndgameUI:
    _OPTIONS = [("CONTINUAR", "continue"), ("VOLTAR AO MENU", "menu")]

    def __init__(self, width: int, height: int):
        self.W = width
        self.H = height
        self.pilot_name = "Piloto"
        self._selection = 0

        self.font_title = pygame.font.SysFont("Consolas", 32, bold=True)
        self.font_pilot = pygame.font.SysFont("Consolas", 18, bold=True)
        self.font_body = pygame.font.SysFont("Consolas", 16)
        self.font_opt = pygame.font.SysFont("Consolas", 17)

    def open(self, pilot_name: str = "Piloto"):
        self.pilot_name = pilot_name or "Piloto"
        self._selection = 0

    def handle_event(self, ev) -> str | None:
        if ev.type != pygame.KEYDOWN:
            return None
        if ev.key == pygame.K_UP:
            self._selection = (self._selection - 1) % len(self._OPTIONS)
        elif ev.key == pygame.K_DOWN:
            self._selection = (self._selection + 1) % len(self._OPTIONS)
        elif ev.key in (pygame.K_RETURN, pygame.K_KP_ENTER):
            return self._OPTIONS[self._selection][1]
        elif ev.key == pygame.K_ESCAPE:
            return "continue"
        return None

    def draw(self, screen: pygame.Surface):
        overlay = pygame.Surface((self.W, self.H), pygame.SRCALPHA)
        overlay.fill((0, 0, 20, 230))
        screen.blit(overlay, (0, 0))

        # Borda decorativa
        pygame.draw.rect(screen, (0, 220, 140),
                         (30, 30, self.W - 60, self.H - 60), width=2)

        cy = self.H // 2 - 140

        # Título
        title = self.font_title.render("MISSÃO CONCLUÍDA", True, (80, 255, 180))
        screen.blit(title, title.get_rect(center=(self.W // 2, cy)))
        cy += 48

        # Nome do piloto
        pilot = self.font_pilot.render(
            f"Piloto: {self.pilot_name}", True, (200, 230, 255)
        )
        screen.blit(pilot, pilot.get_rect(center=(self.W // 2, cy)))
        cy += 40

        # Linha divisória
        pygame.draw.line(screen, (0, 150, 110),
                         (self.W // 2 - 200, cy), (self.W // 2 + 200, cy), 1)
        cy += 20

        # Epílogo
        for line in EPILOGUE:
            surf = self.font_body.render(line, True, (180, 210, 255))
            screen.blit(surf, surf.get_rect(center=(self.W // 2, cy)))
            cy += 24

        cy += 16

        # Opções
        for i, (label, _) in enumerate(self._OPTIONS):
            color = (255, 220, 80) if i == self._selection else (140, 165, 190)
            prefix = "▸ " if i == self._selection else "  "
            surf = self.font_opt.render(prefix + label, True, color)
            screen.blit(surf, surf.get_rect(center=(self.W // 2, cy + i * 36)))
