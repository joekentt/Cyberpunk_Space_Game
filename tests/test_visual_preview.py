"""
Preview headless do main_pygame.py — renderiza um frame estilo Pygame
usando só Pillow. Útil para inspecionar o look do jogo sem rodar pygame.
"""
import os
import sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import random
import math
from PIL import Image, ImageDraw, ImageFont

from visual_engine.procedural_assembler import ProceduralShipAssembler


class MockShip:
    def __init__(self, ship_class, faction, x, y, rotation=0, is_player=False, name=None):
        self.ship_class = ship_class
        self.faction = faction
        self.position = [x, y]
        self.rotation = rotation
        self.is_player = is_player
        self.name = name or f"{faction}-{ship_class}"


def render_frame(out_path):
    W, H = 960, 640
    BG = (8, 8, 18)

    img = Image.new("RGB", (W, H), BG)
    draw = ImageDraw.Draw(img)

    # ---- Fundo parallax (estrelas) ----
    rng = random.Random(42)
    for _ in range(120):
        x = rng.randint(0, W)
        y = rng.randint(0, H)
        size = rng.choice([1, 1, 1, 2])
        intensity = rng.choice([60, 90, 130, 180, 220])
        color = (intensity, intensity, min(255, intensity + 30))
        if size == 1:
            draw.point((x, y), fill=color)
        else:
            draw.ellipse([x, y, x + 1, y + 1], fill=color)

    # ---- Naves ----
    ships = [
        MockShip("Small", "United Humans", W // 2, H // 2, rotation=-30, is_player=True, name="Viper [VOCÊ]"),
        MockShip("Small", "Orcs", 200, 150, rotation=135),
        MockShip("Medium", "Marth", W - 200, 150, rotation=-135),
        MockShip("Small", "Pirates", 200, H - 150, rotation=45),
        MockShip("Large", "Independent", W - 250, H - 180, rotation=-90),
    ]

    assembler = ProceduralShipAssembler()

    try:
        label_font = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", 11)
        hud_font = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", 12)
        title_font = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", 16)
    except Exception:
        label_font = hud_font = title_font = ImageFont.load_default()

    for ship in ships:
        seed = abs(hash(ship.name)) % 10000
        sprite = assembler.get_ship_image(ship, seed)
        # Rotacionar (Pillow rotaciona anti-horário; -rotation = horário)
        rotated = sprite.rotate(-ship.rotation, resample=Image.BILINEAR, expand=True)

        # Posicionar centralizado
        sx = int(ship.position[0] - rotated.width / 2)
        sy = int(ship.position[1] - rotated.height / 2)
        img.paste(rotated, (sx, sy), rotated)

        # Label
        if not ship.is_player:
            text = ship.faction
            tw = draw.textlength(text, font=label_font)
            tx = int(ship.position[0] - tw / 2)
            ty = sy - 14
            draw.text((tx, ty), text, fill=(180, 200, 220), font=label_font)
        else:
            text = ship.name
            tw = draw.textlength(text, font=label_font)
            tx = int(ship.position[0] - tw / 2)
            ty = sy - 14
            draw.text((tx, ty), text, fill=(0, 220, 255), font=label_font)

    # ---- HUD ----
    # Barras
    bar_x, bar_y = 20, 20
    bar_w, bar_h = 200, 14

    def bar(label, pct, color, y):
        draw.rectangle([bar_x, y, bar_x + bar_w, y + bar_h], fill=(40, 40, 50))
        draw.rectangle([bar_x, y, bar_x + int(bar_w * pct), y + bar_h], fill=color)
        draw.rectangle([bar_x, y, bar_x + bar_w, y + bar_h], outline=(200, 200, 220))
        draw.text((bar_x + bar_w + 10, y), label, fill=(220, 220, 220), font=hud_font)

    bar("SHIELDS", 0.85, (0, 150, 255), bar_y)
    bar("ENERGY", 0.62, (255, 200, 0), bar_y + 24)
    bar("HEAT", 0.30, (255, 70, 30), bar_y + 48)

    # Pips
    pips_text = "PIPS:  W[■■]  S[■■■]  E[■]"
    draw.text((bar_x, bar_y + 76), pips_text, fill=(0, 220, 255), font=hud_font)

    # Velocidade
    draw.text((bar_x, H - 28), "SPEED: 47.3 m/s", fill=(220, 220, 220), font=hud_font)

    # Controles (canto inferior direito)
    controls = ["W = thrust   A/D = rotate", "1/2/3 = realocar PIP (W/S/E)", "ESC = sair"]
    cy = H - 60
    for line in controls:
        tw = draw.textlength(line, font=label_font)
        draw.text((W - tw - 12, cy), line, fill=(140, 160, 180), font=label_font)
        cy += 14

    # FPS
    draw.text((W - 80, 8), "FPS: 60", fill=(100, 120, 140), font=label_font)

    # Título
    draw.text((W // 2 - 130, 8), "Cyberpunk Space RPG", fill=(0, 220, 255), font=title_font)

    img.save(out_path)
    print(f"Frame preview salvo em: {out_path}")
    return img


if __name__ == "__main__":
    render_frame("/tmp/space_rpg_sprites/_frame_preview.png")
