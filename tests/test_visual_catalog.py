"""
Vitrine visual do catálogo de naves Tier 1.
Renderiza cada modelo com seu sprite + stats em formato de "ficha técnica".
Carrega dados do data/ships.json (não hardcoded).
"""
import os
import sys
import json
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from PIL import Image, ImageDraw, ImageFont
from visual_engine.procedural_assembler import ProceduralShipAssembler
from entities.ship import Ship


def load_ships():
    """Carrega catálogo do data/ships.json."""
    path = os.path.join(
        os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
        "data", "ships.json"
    )
    with open(path, "r") as f:
        return json.load(f)["ships"]


def render_catalog():
    ships_data = load_ships()
    assembler = ProceduralShipAssembler()

    # Cores e fontes
    BG = (12, 14, 24)
    CARD_BG = (20, 22, 35)
    ACCENT = (0, 220, 255)
    TEXT = (220, 230, 240)
    DIM = (140, 160, 180)
    LABEL = (110, 130, 150)

    try:
        title_font = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", 32)
        ship_name_font = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", 22)
        role_font = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", 14)
        label_font = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", 11)
        spec_font = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", 12)
        desc_font = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", 11)
    except Exception:
        title_font = ship_name_font = role_font = ImageFont.load_default()
        label_font = spec_font = desc_font = ImageFont.load_default()

    # Layout: 2 colunas × N linhas (4 naves = 2x2)
    card_w, card_h = 540, 340
    margin = 24
    cols = 2
    rows = (len(ships_data) + cols - 1) // cols
    W = margin + cols * (card_w + margin)
    H = 80 + rows * (card_h + margin) + margin

    img = Image.new("RGB", (W, H), BG)
    draw = ImageDraw.Draw(img)

    # Grid de fundo
    for i in range(0, W, 40):
        draw.line([(i, 0), (i, H)], fill=(18, 20, 30), width=1)
    for j in range(0, H, 40):
        draw.line([(0, j), (W, j)], fill=(18, 20, 30), width=1)

    # Título geral
    draw.text((margin, 24), "CATÁLOGO DE NAVES — TIER 1", fill=ACCENT, font=title_font)
    draw.text((margin, 60), "Modelos disponíveis no início do jogo", fill=DIM, font=desc_font)

    # Cards
    for i, sd in enumerate(ships_data):
        row = i // cols
        col = i % cols
        x0 = margin + col * (card_w + margin)
        y0 = 90 + row * (card_h + margin)

        # Fundo do card
        draw.rectangle([x0, y0, x0 + card_w, y0 + card_h], fill=CARD_BG)

        # Brackets nos cantos
        bracket_color = ACCENT
        blen = 18
        # cantos
        draw.line([(x0, y0), (x0 + blen, y0)], fill=bracket_color, width=2)
        draw.line([(x0, y0), (x0, y0 + blen)], fill=bracket_color, width=2)
        draw.line([(x0 + card_w, y0), (x0 + card_w - blen, y0)], fill=bracket_color, width=2)
        draw.line([(x0 + card_w, y0), (x0 + card_w, y0 + blen)], fill=bracket_color, width=2)
        draw.line([(x0, y0 + card_h), (x0 + blen, y0 + card_h)], fill=bracket_color, width=2)
        draw.line([(x0, y0 + card_h), (x0, y0 + card_h - blen)], fill=bracket_color, width=2)
        draw.line([(x0 + card_w, y0 + card_h), (x0 + card_w - blen, y0 + card_h)], fill=bracket_color, width=2)
        draw.line([(x0 + card_w, y0 + card_h), (x0 + card_w, y0 + card_h - blen)], fill=bracket_color, width=2)

        # Gerar sprite (sempre paleta United Humans para padrão de catálogo)
        ship = Ship.from_dict(sd)
        ship.faction = "United Humans"
        sprite = assembler.get_ship_image(ship, seed=42)

        # Scale dinâmico: alvo de ~240px de largura, scale inteiro
        target_w = 240
        scale = max(2, min(4, target_w // sprite.width))
        big = sprite.resize((sprite.width * scale, sprite.height * scale), Image.NEAREST)

        # Zona do sprite: lado esquerdo do card (largura fixa de 280px)
        sprite_zone_w = 280
        sprite_x = x0 + (sprite_zone_w - big.width) // 2
        sprite_y = y0 + (card_h - big.height) // 2 - 20  # leve offset pra cima
        img.paste(big, (sprite_x, sprite_y), big)

        # Painel direito: nome, role, stats — posição FIXA
        info_x = x0 + sprite_zone_w + 10

        # Nome da nave
        draw.text((info_x, y0 + 20), sd["name"], fill=ACCENT, font=ship_name_font)

        # Role + tier
        role_text = f"{sd['role'].upper()} · TIER {sd.get('tier', 1)} · {sd['class']}"
        draw.text((info_x, y0 + 52), role_text, fill=DIM, font=role_font)

        # Linha divisória
        draw.line([(info_x, y0 + 78), (x0 + card_w - 20, y0 + 78)],
                  fill=(60, 80, 100), width=1)

        # Stats
        stats = sd["base_stats"]
        hp = sd.get("hardpoints", {})
        hp_str_parts = []
        if hp.get("weapon_small", 0): hp_str_parts.append(f"{hp['weapon_small']}S")
        if hp.get("weapon_medium", 0): hp_str_parts.append(f"{hp['weapon_medium']}M")
        if hp.get("weapon_large", 0): hp_str_parts.append(f"{hp['weapon_large']}L")
        if hp.get("utility", 0): hp_str_parts.append(f"{hp['utility']}U")
        hp_str = " + ".join(hp_str_parts) if hp_str_parts else "—"

        rows_of_stats = [
            ("CASCO", f"{stats.get('hull_hp', '—')} HP"),
            ("ESCUDOS", f"{stats.get('shields_max', '—')}"),
            ("ENERGIA", f"{stats.get('energy_capacity', '—')}"),
            ("MASSA", f"{stats.get('mass', '—')} t"),
            ("CARGA", f"{stats.get('cargo_capacity', '—')} m³"),
            ("HARDPTS", hp_str),
        ]
        sy = y0 + 90
        for k, v in rows_of_stats:
            draw.text((info_x, sy), k, fill=LABEL, font=label_font)
            draw.text((info_x + 70, sy), v, fill=TEXT, font=spec_font)
            sy += 18

        # Preço (com destaque)
        price = sd.get("base_price", 0)
        if price > 0:
            price_text = f"⚙ {price:,} cr".replace(",", ".")
        else:
            price_text = "⚙ Padrão (grátis)"
        draw.text((info_x, sy + 4), price_text, fill=ACCENT, font=role_font)

        # Descrição (na parte inferior do card, abaixo do sprite)
        desc = sd.get("description", "")
        desc_x = x0 + 24
        desc_y = y0 + card_h - 50
        # Quebrar em até 2 linhas
        words = desc.split()
        lines = []
        line = ""
        max_width = card_w - 48
        for word in words:
            test = (line + " " + word).strip()
            if draw.textlength(test, font=desc_font) <= max_width:
                line = test
            else:
                lines.append(line)
                line = word
                if len(lines) >= 2:
                    line = line + "..."
                    break
        if line and len(lines) < 3:
            lines.append(line)
        for li, ln in enumerate(lines[:3]):
            draw.text((desc_x, desc_y + li * 13), ln, fill=DIM, font=desc_font)

    out_path = "/tmp/space_rpg_sprites/_catalog_tier1.png"
    img.save(out_path)
    print(f"Catálogo Tier 1 salvo em: {out_path}")
    return img


if __name__ == "__main__":
    os.makedirs("/tmp/space_rpg_sprites", exist_ok=True)
    render_catalog()
