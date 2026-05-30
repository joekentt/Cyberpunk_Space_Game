"""
StationGenerator — sprite procedural de estações espaciais.

Estações compartilham várias técnicas do SpriteGenerator (paleta, camadas,
simetria) mas têm diferenças importantes:
  - Não têm motores
  - São maiores (canvas 180-240px)
  - Múltiplas docas visíveis (em formato cruz/hexágono)
  - Várias "janelas" iluminadas
  - Painéis solares grandes
  - Anel central rotativo (overlay separado, render fora do polígono)
"""
from PIL import Image, ImageDraw
import math
import random
from typing import Dict, List, Tuple

from visual_engine.sprite_generator import (
    _profile_to_pixels, _mirror_profile, _darken, _lighten,
)

RGBA = Tuple[int, int, int, int]


# -------------------------------------------------------------- Perfis

STATION_PROFILES: Dict[str, Dict] = {
    "hub_alpha": {
        # Estação em formato de cruz/+ com 4 braços de docking.
        # Hexágono central + braços projetados em todas as direções.
        "hull": [
            # Doca leste (ponta direita)
            (0.95, 0.05),
            (0.95, 0.15),
            (0.75, 0.18),
            # Recuo para o corpo
            (0.55, 0.20),
            # Subida pro braço norte (visto em +Y)
            (0.55, 0.40),
            (0.40, 0.45),
            (0.20, 0.50),
            # Topo da doca norte
            (0.18, 0.75),
            (0.18, 0.95),
            (-0.18, 0.95),
            (-0.18, 0.75),
            (-0.20, 0.50),
            (-0.40, 0.45),
            (-0.55, 0.40),
            (-0.55, 0.20),
            (-0.75, 0.18),
            (-0.95, 0.15),
            (-0.95, 0.05),
        ],
        "canvas_size": 200,
        "fill_ratio": 0.94,
        "cockpit": [
            # Núcleo central (controle iluminado)
            (0.0, 0.0, 0.10, 0.10),
            # Janelas dispersas pelo casco - vão ser espelhadas
            (0.65, 0.10, 0.025, 0.025),
            (0.50, 0.10, 0.025, 0.025),
            (0.35, 0.10, 0.025, 0.025),
            (0.20, 0.10, 0.025, 0.025),
            (-0.20, 0.10, 0.025, 0.025),
            (-0.35, 0.10, 0.025, 0.025),
            (-0.50, 0.10, 0.025, 0.025),
            (-0.65, 0.10, 0.025, 0.025),
            # Janelas no braço norte (lado + Y)
            (0.10, 0.30, 0.025, 0.025),
            (-0.10, 0.30, 0.025, 0.025),
            (0.10, 0.55, 0.025, 0.025),
            (-0.10, 0.55, 0.025, 0.025),
            (0.10, 0.80, 0.025, 0.025),
            (-0.10, 0.80, 0.025, 0.025),
        ],
        "engines": [],   # estação não tem motor
        "hardpoints": [
            # Pontos de docking (visíveis nas pontas)
            (0.90, 0.0),
            (0.0, 0.90),
            # Defesas nos cantos
            (0.45, 0.45),
            (-0.45, 0.45),
        ],
        "panel_lines": [
            # Quilha cruzada (visual de "+")
            ((0.85, 0.0), (-0.85, 0.0)),
            ((0.0, 0.85), (0.0, -0.85)),
            # Hexágono central
            ((0.35, 0.0), (0.18, 0.30)),
            ((0.18, 0.30), (-0.18, 0.30)),
            ((-0.18, 0.30), (-0.35, 0.0)),
            ((-0.35, 0.0), (-0.18, -0.30)),
            ((-0.18, -0.30), (0.18, -0.30)),
            ((0.18, -0.30), (0.35, 0.0)),
            # Linhas dos braços
            ((0.55, 0.18), (0.55, -0.18)),
            ((0.75, 0.15), (0.75, -0.15)),
            ((0.18, 0.55), (-0.18, 0.55)),
            ((0.18, 0.75), (-0.18, 0.75)),
        ],
    },
}


# -------------------------------------------------------------- Generator

class StationGenerator:
    """
    Gera sprites de estações espaciais.
    """

    @staticmethod
    def generate_station_sprite(model_id: str,
                                palette: Dict[str, RGBA],
                                seed: int = 0) -> Image.Image:
        profile = STATION_PROFILES.get(model_id, STATION_PROFILES["hub_alpha"])
        size = profile["canvas_size"]
        rng = random.Random(seed)

        img = Image.new("RGBA", (size, size), (0, 0, 0, 0))
        draw = ImageDraw.Draw(img, "RGBA")

        full_outline = _mirror_profile(profile["hull"])
        outline_px = _profile_to_pixels(full_outline, size, profile["fill_ratio"])

        # Sombra (offset diagonal)
        shadow_px = [(x + 3, y + 3) for x, y in outline_px]
        draw.polygon(shadow_px, fill=(0, 0, 0, 100))

        # Casco escuro (base)
        draw.polygon(outline_px, fill=palette["primary_dark"])

        # Casco principal (deslocado 1px pra cima = pseudo-3D)
        hull_px = [(x, y - 1) for x, y in outline_px]
        draw.polygon(hull_px, fill=palette["primary"])

        # Highlight superior - escala 0.82
        inner = [(x * 0.82, y * 0.82) for x, y in profile["hull"]]
        inner_full = _mirror_profile(inner)
        inner_px = _profile_to_pixels(inner_full, size, profile["fill_ratio"])
        draw.polygon(inner_px, fill=palette["primary_light"])
        # Sobrescreve metade inferior com primary (pra manter highlight só em cima)
        StationGenerator._fill_lower_half(draw, img, inner_px, palette["primary"], size)

        # Linhas de painel
        for (a, b) in profile["panel_lines"]:
            pa = _profile_to_pixels([a], size, profile["fill_ratio"])[0]
            pb = _profile_to_pixels([b], size, profile["fill_ratio"])[0]
            draw.line([pa, pb], fill=palette["primary_dark"], width=1)

        # Hardpoints (docking ports)
        for (nx, ny) in profile["hardpoints"]:
            x, y = _profile_to_pixels([(nx, ny)], size, profile["fill_ratio"])[0]
            draw.rectangle([x - 2, y - 2, x + 2, y + 2], fill=palette["primary_dark"])
            draw.point((x, y), fill=palette["secondary"])
            # Espelha
            if abs(ny) > 0.001:
                x2, y2 = _profile_to_pixels([(nx, -ny)], size, profile["fill_ratio"])[0]
                draw.rectangle([x2 - 2, y2 - 2, x2 + 2, y2 + 2], fill=palette["primary_dark"])

        # Janelas (cockpits expandidos - várias luzes)
        center = size / 2
        scale = (size / 2) * profile["fill_ratio"]
        for (cx, cy, rx, ry) in profile["cockpit"]:
            px = center + cx * scale
            py = center - cy * scale
            rxp = max(1, rx * scale)
            ryp = max(1, ry * scale)
            # Halo
            draw.ellipse(
                [px - rxp - 1, py - ryp - 1, px + rxp + 1, py + ryp + 1],
                fill=palette["glow"],
            )
            # Núcleo emissivo
            draw.ellipse(
                [px - rxp, py - ryp, px + rxp, py + ryp],
                fill=palette["accent"],
            )
            # Espelhar verticalmente (cy != 0)
            if abs(cy) > 0.001:
                py2 = center + cy * scale
                draw.ellipse(
                    [px - rxp - 1, py2 - ryp - 1, px + rxp + 1, py2 + ryp + 1],
                    fill=palette["glow"],
                )
                draw.ellipse(
                    [px - rxp, py2 - ryp, px + rxp, py2 + ryp],
                    fill=palette["accent"],
                )

        # Borda final
        outline_color = _darken(palette["primary_dark"], 0.3)
        pts = outline_px + [outline_px[0]]
        for i in range(len(pts) - 1):
            draw.line([pts[i], pts[i + 1]], fill=outline_color, width=1)

        return img

    @staticmethod
    def _fill_lower_half(draw, img, polygon_px, color, size):
        """Pinta metade inferior com a cor primary (mantém highlight só em cima)."""
        mask = Image.new("L", (size, size), 0)
        mdraw = ImageDraw.Draw(mask)
        mdraw.polygon(polygon_px, fill=255)
        mdraw.rectangle([0, 0, size, size // 2], fill=0)
        overlay = Image.new("RGBA", (size, size), color)
        try:
            img.paste(overlay, (0, 0), mask)
        except Exception:
            pass
