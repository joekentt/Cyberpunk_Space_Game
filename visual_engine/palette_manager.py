from typing import Dict, Tuple

RGBA = Tuple[int, int, int, int]


class PaletteManager:
    """
    Gerencia paletas de cores 32-bit (RGBA) por facção.
    Cada paleta define a identidade visual cyberpunk de uma facção.

    Chaves de paleta:
      - primary:        cor principal do casco (mid tone)
      - primary_dark:   sombra/borda inferior do casco (3D fake)
      - primary_light:  highlight do casco
      - secondary:      cor de detalhes/painéis
      - accent:         cor neon (cockpit, motores, luzes emissivas)
      - glow:           accent com alpha reduzido (halo)
    """

    def __init__(self):
        self.palettes: Dict[str, Dict[str, RGBA]] = {
            # United Humans - "Cyberpunk Clássico" (azul cobalto + ciano neon)
            "United Humans": {
                "primary":       (95, 110, 140, 255),
                "primary_dark":  (45, 55, 75, 255),
                "primary_light": (155, 170, 195, 255),
                "secondary":     (70, 85, 110, 255),
                "accent":        (0, 220, 255, 255),
                "glow":          (0, 220, 255, 110),
            },
            # Orcs - "Brutalist apocalíptico" (ferrugem + laranja-fogo)
            "Orcs": {
                "primary":       (110, 70, 50, 255),
                "primary_dark":  (55, 30, 20, 255),
                "primary_light": (165, 115, 85, 255),
                "secondary":     (85, 50, 35, 255),
                "accent":        (255, 90, 30, 255),
                "glow":          (255, 90, 30, 120),
            },
            # Marth - "High-tech avançado" (roxo profundo + magenta neon)
            "Marth": {
                "primary":       (75, 50, 110, 255),
                "primary_dark":  (30, 20, 55, 255),
                "primary_light": (140, 110, 180, 255),
                "secondary":     (55, 35, 85, 255),
                "accent":        (255, 60, 200, 255),
                "glow":          (255, 60, 200, 130),
            },
            # Pirates - "Sucateiro perigoso" (cinza fosco + vermelho-sangue)
            "Pirates": {
                "primary":       (75, 70, 70, 255),
                "primary_dark":  (35, 30, 30, 255),
                "primary_light": (130, 120, 115, 255),
                "secondary":     (55, 50, 50, 255),
                "accent":        (230, 30, 30, 255),
                "glow":          (230, 30, 30, 120),
            },
            # Independent - "Civil/industrial" (cinza neutro + amarelo)
            "Independent": {
                "primary":       (115, 115, 110, 255),
                "primary_dark":  (60, 60, 55, 255),
                "primary_light": (170, 170, 165, 255),
                "secondary":     (90, 90, 85, 255),
                "accent":        (255, 200, 40, 255),
                "glow":          (255, 200, 40, 110),
            },
        }

        # Aliases para resiliência (compat com versões antigas / typos)
        self.aliases = {
            "Humans": "United Humans",
            "Human": "United Humans",
            "Pirate": "Pirates",
            "Orc": "Orcs",
        }

    def get_palette(self, faction: str) -> Dict[str, RGBA]:
        if faction in self.palettes:
            return self.palettes[faction]
        if faction in self.aliases:
            return self.palettes[self.aliases[faction]]
        return self.palettes["Independent"]

    def list_factions(self):
        return list(self.palettes.keys())
