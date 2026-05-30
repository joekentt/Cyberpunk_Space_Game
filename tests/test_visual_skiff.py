"""
Preview dedicado da nave inicial — Skiff Mk I.
Mostra ela em destaque (upscale 8x) e em cena de gameplay.
"""
import os
import sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import random
from PIL import Image, ImageDraw, ImageFont
from visual_engine.procedural_assembler import ProceduralShipAssembler
from visual_engine.palette_manager import PaletteManager


class MockShip:
    def __init__(self, ship_class, faction, x, y, rotation=0,
                 is_player=False, name=None, model_id=None):
        self.ship_class = ship_class
        self.faction = faction
        self.position = [x, y]
        self.rotation = rotation
        self.is_player = is_player
        self.name = name or f"{faction}-{ship_class}"
        self.model_id = model_id


def render_hero_shot():
    """Renderiza um 'cartão de identidade' da Skiff Mk I."""
    W, H = 800, 500
    BG = (12, 14, 24)
    img = Image.new("RGB", (W, H), BG)
    draw = ImageDraw.Draw(img)

    try:
        title_font = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", 28)
        sub_font = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", 16)
        label_font = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", 12)
        spec_font = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", 13)
    except Exception:
        title_font = sub_font = label_font = spec_font = ImageFont.load_default()

    # Grid de tela
    for i in range(0, W, 40):
        draw.line([(i, 0), (i, H)], fill=(20, 22, 35), width=1)
    for j in range(0, H, 40):
        draw.line([(0, j), (W, j)], fill=(20, 22, 35), width=1)

    assembler = ProceduralShipAssembler()
    skiff = MockShip("Small", "United Humans", 0, 0, model_id="starter_skiff")
    sprite = assembler.get_ship_image(skiff, seed=1)

    # Upscale 6x pra herói
    big = sprite.resize((sprite.width * 6, sprite.height * 6), Image.NEAREST)
    bx = 60
    by = (H - big.height) // 2
    img.paste(big, (bx, by), big)

    # Brackets de "design spec" em volta do sprite
    bracket_color = (0, 220, 255)
    blen = 30
    margin = 10
    x1, y1 = bx - margin, by - margin
    x2, y2 = bx + big.width + margin, by + big.height + margin
    # cantos
    draw.line([(x1, y1), (x1 + blen, y1)], fill=bracket_color, width=2)
    draw.line([(x1, y1), (x1, y1 + blen)], fill=bracket_color, width=2)
    draw.line([(x2, y1), (x2 - blen, y1)], fill=bracket_color, width=2)
    draw.line([(x2, y1), (x2, y1 + blen)], fill=bracket_color, width=2)
    draw.line([(x1, y2), (x1 + blen, y2)], fill=bracket_color, width=2)
    draw.line([(x1, y2), (x1, y2 - blen)], fill=bracket_color, width=2)
    draw.line([(x2, y2), (x2 - blen, y2)], fill=bracket_color, width=2)
    draw.line([(x2, y2), (x2, y2 - blen)], fill=bracket_color, width=2)

    # Painel de specs à direita
    panel_x = 470
    draw.text((panel_x, 50), "SKIFF Mk I", fill=(0, 220, 255), font=title_font)
    draw.text((panel_x, 84), "Caça civil — produção em massa", fill=(180, 200, 220), font=sub_font)

    draw.line([(panel_x, 115), (panel_x + 280, 115)], fill=(60, 80, 100), width=1)

    specs = [
        ("CLASSE",     "Small"),
        ("MODELO",     "starter_skiff"),
        ("MASSA",      "120 t"),
        ("ENERGIA",    "100 / 100"),
        ("DISSIPAÇÃO", "8 u/s (alta — corre frio)"),
        ("HARDPOINTS", "2 × Small + 1 utilitário"),
        ("CASCO",      "80 HP"),
        ("ESCUDO",     "100 / 100"),
        ("CARGA",      "10 m³ (pequena)"),
    ]
    y = 130
    for k, v in specs:
        draw.text((panel_x, y), k, fill=(120, 140, 160), font=label_font)
        draw.text((panel_x + 110, y), v, fill=(220, 230, 240), font=spec_font)
        y += 20

    # Rodapé
    draw.line([(panel_x, y + 8), (panel_x + 280, y + 8)], fill=(60, 80, 100), width=1)
    note = "Nave inicial padrão. Todo piloto começa com uma."
    draw.text((panel_x, y + 16), note, fill=(160, 180, 200), font=spec_font)

    out = "/tmp/space_rpg_sprites/_skiff_hero.png"
    img.save(out)
    print(f"Hero shot salvo em: {out}")
    return img


def render_skiff_in_scene():
    """Cena de gameplay com a Skiff Mk I em ação contra naves do catálogo Tier 1."""
    W, H = 960, 640
    BG = (8, 8, 18)
    img = Image.new("RGB", (W, H), BG)
    draw = ImageDraw.Draw(img)

    # Estrelas
    rng = random.Random(7)
    for _ in range(140):
        x = rng.randint(0, W)
        y = rng.randint(0, H)
        intensity = rng.choice([50, 80, 120, 180, 230])
        draw.point((x, y), fill=(intensity, intensity, min(255, intensity + 30)))

    assembler = ProceduralShipAssembler()

    # Skiff Mk I do jogador no centro, levemente angulada
    player = MockShip("Small", "United Humans", W // 2, H // 2,
                      rotation=-20, is_player=True, name="Skiff Mk I",
                      model_id="starter_skiff")

    # NPCs do catálogo Tier 1 — mostram a variedade visual
    npcs = [
        MockShip("Small", "Pirates", 200, 150, rotation=140,
                 name="Wasp Pirate", model_id="wasp_combat"),
        MockShip("Small", "Independent", W - 220, 180, rotation=-130,
                 name="Albatross", model_id="albatross_explorer"),
        MockShip("Medium", "Independent", W - 240, H - 180, rotation=-90,
                 name="Mule", model_id="mule_trader"),
        MockShip("Medium", "Marth", 220, H - 160, rotation=45,
                 name="Marth Frigate", model_id=None),  # frigata genérica Marth
    ]

    try:
        label_font = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", 11)
        hud_font = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", 12)
        title_font = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", 16)
    except Exception:
        label_font = hud_font = title_font = ImageFont.load_default()

    for ship in [player] + npcs:
        seed = abs(hash(ship.name)) % 10000
        sprite = assembler.get_ship_image(ship, seed)
        rotated = sprite.rotate(-ship.rotation, resample=Image.BILINEAR, expand=True)
        sx = int(ship.position[0] - rotated.width / 2)
        sy = int(ship.position[1] - rotated.height / 2)
        img.paste(rotated, (sx, sy), rotated)

        label_text = ship.name if ship.is_player else ship.faction
        label_color = (0, 220, 255) if ship.is_player else (180, 200, 220)
        tw = draw.textlength(label_text, font=label_font)
        draw.text((int(ship.position[0] - tw / 2), sy - 14),
                  label_text, fill=label_color, font=label_font)

    # HUD básico
    bar_x, bar_y, bar_w, bar_h = 20, 20, 200, 14

    def bar(label, pct, color, y):
        draw.rectangle([bar_x, y, bar_x + bar_w, y + bar_h], fill=(40, 40, 50))
        draw.rectangle([bar_x, y, bar_x + int(bar_w * pct), y + bar_h], fill=color)
        draw.rectangle([bar_x, y, bar_x + bar_w, y + bar_h], outline=(200, 200, 220))
        draw.text((bar_x + bar_w + 10, y), label, fill=(220, 220, 220), font=hud_font)

    bar("SHIELDS", 1.0, (0, 150, 255), bar_y)
    bar("ENERGY", 1.0, (255, 200, 0), bar_y + 24)
    bar("HEAT", 0.05, (255, 70, 30), bar_y + 48)
    draw.text((bar_x, bar_y + 76), "PIPS: W[2] S[2] E[2]", fill=(0, 220, 255), font=hud_font)
    draw.text((bar_x, H - 28), "SPEED: 0.0 m/s — Nova partida", fill=(180, 200, 220), font=hud_font)
    draw.text((W // 2 - 130, 8), "Cyberpunk Space RPG", fill=(0, 220, 255), font=title_font)

    out = "/tmp/space_rpg_sprites/_skiff_scene.png"
    img.save(out)
    print(f"Scene salvo em: {out}")
    return img


if __name__ == "__main__":
    os.makedirs("/tmp/space_rpg_sprites", exist_ok=True)
    render_hero_shot()
    render_skiff_in_scene()
