"""
Preview ANTES/DEPOIS do detalhamento dos sprites de nave.

Mostra as 4 naves do catálogo (Skiff, Wasp, Albatross, Mule) lado a lado:
coluna ANTES (PNGs salvos em /tmp/space_rpg_sprites/before/ antes da
refatoração) vs coluna DEPOIS (geradas ao vivo pelo SpriteGenerator atual).

Foco da revisão: motores com bocal+glow, luzes de navegação, faixa emissiva,
linhas de painel em bisel e sombreamento de volume.
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from PIL import Image, ImageDraw, ImageFont
from visual_engine.sprite_generator import SpriteGenerator
from visual_engine.palette_manager import PaletteManager

BEFORE_DIR = "/tmp/space_rpg_sprites/before"
OUT = "/tmp/space_rpg_sprites/_detailing_before_after.png"

SHIPS = [
    ("starter_skiff", "Small",  "United Humans", "Skiff Mk I"),
    ("wasp_combat",   "Small",  "Pirates",       "Wasp"),
    ("albatross_explorer", "Small", "Independent", "Albatross"),
    ("mule_trader",   "Medium", "Independent",   "Mule"),
]

DISP = 4  # fator de upscale na exibição


def _font(sz, bold=True):
    name = "DejaVuSans-Bold.ttf" if bold else "DejaVuSans.ttf"
    try:
        return ImageFont.truetype(f"/usr/share/fonts/truetype/dejavu/{name}", sz)
    except Exception:
        return ImageFont.load_default()


def load_before(model_id):
    """Carrega o PNG 'antes' (salvo em 8x) e retorna no tamanho nativo."""
    path = os.path.join(BEFORE_DIR, f"{model_id}.png")
    if not os.path.exists(path):
        return None
    img = Image.open(path).convert("RGBA")
    # foi salvo em 8x NEAREST → volta ao nativo de forma exata
    return img.resize((img.width // 8, img.height // 8), Image.NEAREST)


def gen_after(model_id, klass, faction):
    pm = PaletteManager()
    return SpriteGenerator.generate_ship_sprite(
        klass, pm.get_palette(faction), seed=7, model_id=model_id)


def paste_centered(canvas, sprite_native, cell_box, panel_bg):
    """Desenha um painel e cola o sprite (upscaled) centralizado nele."""
    x0, y0, x1, y1 = cell_box
    cd = ImageDraw.Draw(canvas)
    cd.rectangle(cell_box, fill=panel_bg, outline=(40, 55, 75))
    if sprite_native is None:
        cd.text(((x0 + x1) // 2 - 20, (y0 + y1) // 2), "—", fill=(120, 130, 150),
                font=_font(20))
        return
    big = sprite_native.resize(
        (sprite_native.width * DISP, sprite_native.height * DISP), Image.NEAREST)
    px = x0 + ((x1 - x0) - big.width) // 2
    py = y0 + ((y1 - y0) - big.height) // 2
    canvas.alpha_composite(big, (px, py))


def main():
    os.makedirs("/tmp/space_rpg_sprites", exist_ok=True)

    cell = 80 * DISP + 24          # célula quadrada (cabe o maior: Mule 80px)
    name_col = 150
    gap = 16
    header_h = 90
    col_w = cell
    W = name_col + gap + col_w + gap + col_w + gap
    H = header_h + len(SHIPS) * (cell + gap) + gap

    canvas = Image.new("RGBA", (W, H), (10, 12, 22, 255))
    draw = ImageDraw.Draw(canvas)

    # grid de fundo
    for gx in range(0, W, 40):
        draw.line([(gx, 0), (gx, H)], fill=(16, 19, 30, 255), width=1)
    for gy in range(0, H, 40):
        draw.line([(0, gy), (W, gy)], fill=(16, 19, 30, 255), width=1)

    draw.text((gap, 22), "Detalhamento de naves — ANTES / DEPOIS",
              fill=(0, 220, 255), font=_font(26))
    draw.text((gap, 56),
              "motores c/ bocal+glow · luzes de navegação · tron line · bisel de painel · volume",
              fill=(150, 170, 190), font=_font(12, bold=False))

    # cabeçalhos de coluna
    col1_x = name_col + gap
    col2_x = col1_x + col_w + gap
    draw.text((col1_x + col_w // 2 - 28, header_h - 24), "ANTES",
              fill=(150, 160, 175), font=_font(16))
    draw.text((col2_x + col_w // 2 - 32, header_h - 24), "DEPOIS",
              fill=(80, 230, 160), font=_font(16))

    name_font = _font(15)
    fac_font = _font(11, bold=False)

    for i, (model_id, klass, faction, name) in enumerate(SHIPS):
        cy = header_h + i * (cell + gap)
        # rótulo da nave
        draw.text((gap, cy + cell // 2 - 16), name, fill=(220, 230, 240),
                  font=name_font)
        draw.text((gap, cy + cell // 2 + 4), faction, fill=(130, 150, 170),
                  font=fac_font)

        before = load_before(model_id)
        after = gen_after(model_id, klass, faction)

        paste_centered(canvas, before, (col1_x, cy, col1_x + col_w, cy + cell),
                       (18, 20, 30, 255))
        paste_centered(canvas, after, (col2_x, cy, col2_x + col_w, cy + cell),
                       (18, 24, 34, 255))

    canvas.convert("RGB").save(OUT)
    print(f"Comparativo salvo em: {OUT}")
    return OUT


if __name__ == "__main__":
    main()
