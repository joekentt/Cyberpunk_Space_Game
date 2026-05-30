"""
Teste headless de geração de sprites.

Gera:
  1. PNGs individuais de cada (classe x facção x seed) em /tmp/sprites/
  2. Uma 'contact sheet' montando uma grade visual para inspeção rápida.

Não requer pygame — só Pillow.
"""

import os
import sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from PIL import Image
from visual_engine.palette_manager import PaletteManager
from visual_engine.sprite_generator import SpriteGenerator, SHIP_PROFILES


# Mock de Ship pra não precisar instanciar a entidade real
class MockShip:
    def __init__(self, ship_class, faction):
        self.ship_class = ship_class
        self.faction = faction


def generate_all_sprites(out_dir: str):
    os.makedirs(out_dir, exist_ok=True)
    factions = ["United Humans", "Orcs", "Marth", "Pirates", "Independent"]
    classes = ["Small", "Medium", "Large"]
    seeds = [1, 42, 1337]

    palette_mgr = PaletteManager()
    sprite_gen = SpriteGenerator()

    generated = []
    for cls in classes:
        for fac in factions:
            for seed in seeds:
                palette = palette_mgr.get_palette(fac)
                img = sprite_gen.generate_ship_sprite(cls, palette, seed=seed)

                # Upscale 4x para visualização (vendo pixel art ampliada)
                upscaled = img.resize(
                    (img.width * 4, img.height * 4),
                    Image.NEAREST,
                )

                fname = f"{cls}_{fac.replace(' ', '_')}_seed{seed}.png"
                path = os.path.join(out_dir, fname)
                upscaled.save(path)
                generated.append((cls, fac, seed, img))

    print(f"Gerados {len(generated)} sprites em {out_dir}")
    return generated


def build_contact_sheet(generated, out_path: str):
    """
    Monta uma grade visual: linhas = facção, colunas = classe (seed=42 só).
    """
    factions = ["United Humans", "Orcs", "Marth", "Pirates", "Independent"]
    classes = ["Small", "Medium", "Large"]

    # Pega só a seed=42 pra grade principal
    by_key = {(c, f): img for (c, f, s, img) in generated if s == 42}

    # Cada célula tem espaço para a maior nave (Large = 96px) com upscale 3x = 288
    cell = 320
    pad = 20
    title_h = 50
    label_w = 200

    cols = len(classes)
    rows = len(factions)
    sheet_w = label_w + cols * cell + (cols + 1) * pad
    sheet_h = title_h + rows * cell + (rows + 1) * pad

    sheet = Image.new("RGB", (sheet_w, sheet_h), (15, 15, 22))
    from PIL import ImageDraw, ImageFont
    draw = ImageDraw.Draw(sheet)

    try:
        font = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", 22)
        small_font = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", 16)
    except Exception:
        font = ImageFont.load_default()
        small_font = font

    # Título
    draw.text((pad, 10), "Cyberpunk Space RPG — Sprite Sheet (seed=42)",
              fill=(0, 220, 255), font=font)

    # Headers das colunas (classes)
    for j, cls in enumerate(classes):
        x = label_w + pad + j * (cell + pad)
        draw.text((x + cell // 2 - 30, title_h - 30), cls,
                  fill=(255, 255, 255), font=small_font)

    # Linhas
    for i, fac in enumerate(factions):
        y = title_h + pad + i * (cell + pad)
        # Label da facção
        palette = PaletteManager().get_palette(fac)
        accent = palette["accent"][:3]
        draw.text((pad, y + cell // 2 - 12), fac,
                  fill=accent, font=small_font)

        # Sprites
        for j, cls in enumerate(classes):
            x = label_w + pad + j * (cell + pad)
            img = by_key.get((cls, fac))
            if img is None:
                continue
            # Upscale para o tamanho da célula
            scale = cell // img.width
            up = img.resize((img.width * scale, img.height * scale), Image.NEAREST)
            # Centralizar
            ox = x + (cell - up.width) // 2
            oy = y + (cell - up.height) // 2
            sheet.paste(up, (ox, oy), up)

    sheet.save(out_path)
    print(f"Contact sheet salva em {out_path}")
    return sheet


if __name__ == "__main__":
    out_dir = "/tmp/space_rpg_sprites"
    generated = generate_all_sprites(out_dir)
    build_contact_sheet(generated, "/tmp/space_rpg_sprites/_contact_sheet.png")
