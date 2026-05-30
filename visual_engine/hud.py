import pygame
from typing import Dict

class HUD:
    def __init__(self, width: int, height: int):
        self.width = width
        self.height = height
        self.font = pygame.font.SysFont("Consolas", 14)
        self.title_font = pygame.font.SysFont("Consolas", 18, bold=True)

    def draw(self, screen: pygame.Surface, player_ship):
        """
        Desenha barras de status e informações do jogador.
        """
        # Margem e dimensões das barras
        margin = 20
        bar_width = 200
        bar_height = 15
        
        # 1. Barra de Escudos (Azul)
        shield_pct = player_ship.current_shields / player_ship.max_shields
        self._draw_bar(screen, margin, margin, bar_width, bar_height, shield_pct, (0, 150, 255), "SHIELDS")
        
        # 2. Barra de Energia (Amarelo)
        energy_pct = player_ship.current_energy / player_ship.energy_capacity
        self._draw_bar(screen, margin, margin + 30, bar_width, bar_height, energy_pct, (255, 200, 0), "ENERGY")
        
        # 3. Barra de Calor (Vermelho)
        heat_pct = min(1.0, player_ship.current_heat / 100.0) # Assume 100 como limite crítico
        heat_color = (255, 50, 0) if heat_pct < 0.8 else (255, 255, 255) # Pisca se crítico
        self._draw_bar(screen, margin, margin + 60, bar_width, bar_height, heat_pct, heat_color, "HEAT")

        # 4. Distribuição de Pips (W-S-E)
        pips_text = f"PIPS: W[{player_ship.pips['weapons']}] S[{player_ship.pips['shields']}] E[{player_ship.pips['engines']}]"
        self._draw_text(screen, pips_text, margin, margin + 90)

        # 5. Velocidade e Créditos (Canto inferior esquerdo)
        speed = (player_ship.velocity[0]**2 + player_ship.velocity[1]**2)**0.5
        self._draw_text(screen, f"SPEED: {speed:.1f} m/s", margin, self.height - 40)

    def _draw_bar(self, screen, x, y, w, h, pct, color, label):
        # Fundo da barra
        pygame.draw.rect(screen, (50, 50, 50), (x, y, w, h))
        # Preenchimento
        pygame.draw.rect(screen, color, (x, y, int(w * pct), h))
        # Borda
        pygame.draw.rect(screen, (200, 200, 200), (x, y, w, h), 1)
        # Label
        text = self.font.render(label, True, (255, 255, 255))
        screen.blit(text, (x + w + 10, y))

    def _draw_text(self, screen, text, x, y, color=(255, 255, 255)):
        img = self.font.render(text, True, color)
        screen.blit(img, (x, y))
