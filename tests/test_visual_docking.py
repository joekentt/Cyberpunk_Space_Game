"""
Preview visual de docking — 2 frames:
  1. Player aproximando da estação (prompt F)
  2. UI do mercado de naves (overlay quando atracado)
"""
import os
import sys
import math
import random
import json
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from PIL import Image, ImageDraw, ImageFont
from visual_engine.procedural_assembler import ProceduralShipAssembler
from visual_engine.station_generator import StationGenerator
from visual_engine.palette_manager import PaletteManager


class MockShip:
    def __init__(self, ship_class, faction, x, y, rotation=0,
                 is_player=False, name="", model_id=None):
        self.ship_class = ship_class
        self.faction = faction
        self.position = [x, y]
        self.rotation = rotation
        self.is_player = is_player
        self.name = name
        self.model_id = model_id


def render_approach_scene():
    W, H = 960, 640
    BG = (8, 8, 18)
    img = Image.new("RGB", (W, H), BG)
    draw = ImageDraw.Draw(img)

    # Estrelas
    rng = random.Random(13)
    for _ in range(140):
        x = rng.randint(0, W); y = rng.randint(0, H)
        intensity = rng.choice([50, 80, 120, 180, 230])
        draw.point((x, y), fill=(intensity, intensity, min(255, intensity + 30)))

    try:
        label_font = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", 11)
        hud_font = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", 12)
        prompt_font = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", 20)
        title_font = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", 16)
    except Exception:
        label_font = hud_font = prompt_font = title_font = ImageFont.load_default()

    # Renderizar estação
    pm = PaletteManager()
    station_gen = StationGenerator()
    station_palette = pm.get_palette("United Humans")
    station_sprite = station_gen.generate_station_sprite("hub_alpha", station_palette, seed=42)

    station_x, station_y = W // 2 + 80, H // 2 - 20
    sx = station_x - station_sprite.width // 2
    sy = station_y - station_sprite.height // 2
    img.paste(station_sprite, (sx, sy), station_sprite)

    # Anel de docking (verde porque player está dentro)
    radius = 180
    overlay = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    od = ImageDraw.Draw(overlay)
    od.ellipse([station_x - radius, station_y - radius,
                station_x + radius, station_y + radius],
               outline=(60, 220, 120, 100), width=2)
    img.paste(overlay, (0, 0), overlay)

    # Player (Skiff) aproximando, dentro do raio
    assembler = ProceduralShipAssembler()
    skiff = MockShip("Small", "United Humans", station_x - 130, station_y + 60,
                     rotation=-25, is_player=True, name="Skiff Mk I",
                     model_id="starter_skiff")
    sprite = assembler.get_ship_image(skiff, seed=1)
    rotated = sprite.rotate(-skiff.rotation, resample=Image.BILINEAR, expand=True)
    psx = int(skiff.position[0] - rotated.width / 2)
    psy = int(skiff.position[1] - rotated.height / 2)
    img.paste(rotated, (psx, psy), rotated)

    # Label do player
    label = "Skiff Mk I"
    tw = draw.textlength(label, font=label_font)
    draw.text((int(skiff.position[0] - tw / 2), psy - 14),
              label, fill=(0, 220, 255), font=label_font)

    # Label da estação
    sname = "Hub Alpha"
    tw = draw.textlength(sname, font=title_font)
    draw.text((station_x - tw / 2, sy - 24),
              sname, fill=(0, 220, 255), font=title_font)

    # HUD
    bar_x, bar_y, bar_w, bar_h = 20, 20, 200, 14

    def bar(label, pct, color, y):
        draw.rectangle([bar_x, y, bar_x + bar_w, y + bar_h], fill=(40, 40, 50))
        draw.rectangle([bar_x, y, bar_x + int(bar_w * pct), y + bar_h], fill=color)
        draw.rectangle([bar_x, y, bar_x + bar_w, y + bar_h], outline=(200, 200, 220))
        draw.text((bar_x + bar_w + 10, y), label, fill=(220, 220, 220), font=hud_font)

    bar("SHIELDS", 1.0, (0, 150, 255), bar_y)
    bar("ENERGY", 0.95, (255, 200, 0), bar_y + 24)
    bar("HEAT", 0.05, (255, 70, 30), bar_y + 48)

    # Combat HUD
    cy = H - 130
    draw.text((20, cy), "NAVE: Skiff Mk I", fill=(180, 200, 220), font=label_font)
    draw.text((20, cy + 14), "CR: 50.000", fill=(255, 220, 80), font=label_font)
    draw.text((20, cy + 28), "SHIELDS: 100/100", fill=(90, 180, 255), font=label_font)
    draw.text((20, cy + 42), "HULL: 80/80", fill=(255, 130, 90), font=label_font)
    # Barra de cooldown (vazia = pronto)
    bar_y2 = cy + 80
    draw.rectangle([20, bar_y2, 180, bar_y2 + 8], fill=(40, 40, 50))
    draw.rectangle([20, bar_y2, 180, bar_y2 + 8], fill=(80, 255, 100))
    draw.text((190, bar_y2 - 2), "WEAPON", fill=(200, 220, 240), font=label_font)

    # Prompt grande
    prompt_text = "[F] Acoplar em Hub Alpha"
    pw = draw.textlength(prompt_text, font=prompt_font)
    prompt_y = H - 100
    bg = Image.new("RGBA", (int(pw + 24), 36), (0, 0, 0, 180))
    img.paste(bg, (int(W // 2 - pw / 2 - 12), prompt_y - 6), bg)
    draw.text((W // 2 - pw / 2, prompt_y), prompt_text,
              fill=(60, 220, 120), font=prompt_font)

    # Título e FPS
    draw.text((W // 2 - 130, 8), "Cyberpunk Space RPG",
              fill=(0, 220, 255), font=title_font)
    draw.text((W - 80, 8), "FPS: 60", fill=(100, 120, 140), font=label_font)

    out = "/tmp/space_rpg_sprites/_docking_approach.png"
    img.save(out)
    print(f"Approach scene salva em: {out}")
    return img


def render_shipyard_ui():
    """Preview da UI de mercado de naves."""
    W, H = 960, 640
    BG = (5, 8, 18)
    img = Image.new("RGB", (W, H), BG)
    draw = ImageDraw.Draw(img)

    try:
        title_font = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", 28)
        section_font = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", 18)
        body_font = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", 14)
        small_font = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", 12)
    except Exception:
        title_font = section_font = body_font = small_font = ImageFont.load_default()

    # Borda decorativa
    draw.rectangle([20, 20, W - 20, H - 20], outline=(0, 150, 200), width=1)

    # Cabeçalho
    draw.text((40, 36), "⌂ Hub Alpha", fill=(0, 220, 255), font=title_font)
    draw.text((40, 70), "Facção: United Humans   |   Serviços: shipyard, repair, refuel",
              fill=(180, 200, 220), font=body_font)

    # Player info à direita
    cred = "⚙ 50.000 cr"
    cw = draw.textlength(cred, font=section_font)
    draw.text((W - cw - 40, 36), cred, fill=(255, 200, 60), font=section_font)
    ship_info = "Pilotando: Skiff Mk I (Small)"
    sw = draw.textlength(ship_info, font=body_font)
    draw.text((W - sw - 40, 70), ship_info, fill=(180, 200, 220), font=body_font)

    # Linha divisória
    draw.line([(40, 100), (W - 40, 100)], fill=(60, 100, 130), width=1)

    # Mercado de Naves
    draw.text((40, 130), "MERCADO DE NAVES", fill=(0, 200, 240), font=section_font)

    # Lista de naves
    ships_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                              "data", "ships.json")
    with open(ships_path) as f:
        catalog = json.load(f)["ships"]
    purchasable = [s for s in catalog if not s.get("starting_ship", False)]

    list_x = 40
    list_w = 380
    list_y = 160
    selected = 0   # primeiro item selecionado

    for i, sd in enumerate(purchasable):
        row_y = list_y + i * 60
        if i == selected:
            draw.rectangle([list_x, row_y, list_x + list_w, row_y + 54],
                           fill=(30, 60, 90))
            draw.rectangle([list_x, row_y, list_x + list_w, row_y + 54],
                           outline=(0, 200, 240), width=1)
        else:
            draw.rectangle([list_x, row_y, list_x + list_w, row_y + 54],
                           fill=(20, 25, 40))

        draw.text((list_x + 12, row_y + 4), sd["name"],
                  fill=(220, 240, 255), font=section_font)
        role = f"{sd['role']} · {sd['class']}"
        draw.text((list_x + 12, row_y + 30), role,
                  fill=(140, 170, 200), font=small_font)

        # Preço
        price = sd.get("base_price", 0)
        price_text = f"{price:,} cr".replace(",", ".") if price > 0 else "GRÁTIS"
        ok = 50000 >= price
        price_color = (120, 230, 120) if ok else (255, 100, 80)
        pw = draw.textlength(price_text, font=body_font)
        draw.text((list_x + list_w - pw - 12, row_y + 6),
                  price_text, fill=price_color, font=body_font)

    # Painel de detalhes (selecionado: Wasp)
    panel_x = list_x + list_w + 30
    panel_w = W - panel_x - 40
    panel_y = list_y
    panel_h = 380
    draw.rectangle([panel_x, panel_y, panel_x + panel_w, panel_y + panel_h],
                   fill=(15, 20, 35))
    draw.rectangle([panel_x, panel_y, panel_x + panel_w, panel_y + panel_h],
                   outline=(0, 150, 200), width=1)

    selected_ship = purchasable[selected]
    draw.text((panel_x + 16, panel_y + 10), selected_ship["name"],
              fill=(0, 220, 255), font=section_font)
    role = f"{selected_ship['role'].upper()} · TIER {selected_ship.get('tier', 1)} · {selected_ship['class']}"
    draw.text((panel_x + 16, panel_y + 40), role, fill=(140, 170, 200), font=small_font)
    draw.line([(panel_x + 16, panel_y + 64), (panel_x + panel_w - 16, panel_y + 64)],
              fill=(60, 100, 130), width=1)

    # Descrição
    desc = selected_ship.get("description", "")
    desc_y = panel_y + 76
    words = desc.split()
    line = ""
    max_w = panel_w - 32
    lines = []
    for word in words:
        test = (line + " " + word).strip()
        if draw.textlength(test, font=small_font) <= max_w:
            line = test
        else:
            lines.append(line)
            line = word
    if line:
        lines.append(line)
    for ln in lines[:5]:
        draw.text((panel_x + 16, desc_y), ln, fill=(180, 200, 220), font=small_font)
        desc_y += 16

    # Stats
    sy = desc_y + 12
    stats = selected_ship["base_stats"]
    hp = selected_ship.get("hardpoints", {})
    hp_parts = []
    if hp.get("weapon_small", 0): hp_parts.append(f"{hp['weapon_small']}S")
    if hp.get("weapon_medium", 0): hp_parts.append(f"{hp['weapon_medium']}M")
    if hp.get("utility", 0): hp_parts.append(f"{hp['utility']}U")
    hp_str = " + ".join(hp_parts) if hp_parts else "—"
    rows = [
        ("CASCO", f"{stats.get('hull_hp', '—')} HP"),
        ("ESCUDOS", f"{stats.get('shields_max', '—')}"),
        ("ENERGIA", f"{stats.get('energy_capacity', '—')}"),
        ("MASSA", f"{stats.get('mass', '—')} t"),
        ("CARGA", f"{stats.get('cargo_capacity', '—')} m³"),
        ("HARDPOINTS", hp_str),
    ]
    for k, v in rows:
        draw.text((panel_x + 16, sy), k, fill=(120, 140, 160), font=small_font)
        draw.text((panel_x + 130, sy), str(v), fill=(220, 230, 240), font=body_font)
        sy += 20

    # Preço
    price = selected_ship.get("base_price", 0)
    price_text = f"{price:,} cr".replace(",", ".")
    draw.text((panel_x + 16, sy + 12), price_text,
              fill=(120, 230, 120), font=section_font)

    # Help no rodapé
    help_text = "↑↓ navegar   ENTER comprar   ESC voltar"
    hw = draw.textlength(help_text, font=small_font)
    draw.text((W / 2 - hw / 2, H - 28), help_text,
              fill=(120, 140, 160), font=small_font)

    out = "/tmp/space_rpg_sprites/_shipyard_ui.png"
    img.save(out)
    print(f"Shipyard UI salva em: {out}")
    return img


if __name__ == "__main__":
    os.makedirs("/tmp/space_rpg_sprites", exist_ok=True)
    render_approach_scene()
    render_shipyard_ui()
