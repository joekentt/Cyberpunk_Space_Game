"""
Preview de combate em ação — simula um frame médio de tiroteio
e renderiza com Pillow para mostrar o look visual do combate.
"""
import os
import sys
import math
import random
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from PIL import Image, ImageDraw, ImageFont
from visual_engine.procedural_assembler import ProceduralShipAssembler
from visual_engine.palette_manager import PaletteManager


class MockShip:
    def __init__(self, ship_class, faction, x, y, rotation=0,
                 is_player=False, name="", model_id=None, hp=1.0, shields=1.0):
        self.ship_class = ship_class
        self.faction = faction
        self.position = [x, y]
        self.rotation = rotation
        self.is_player = is_player
        self.name = name
        self.model_id = model_id
        self.hp_ratio = hp
        self.shields_ratio = shields


def render_combat_scene():
    W, H = 960, 640
    BG = (8, 8, 18)
    img = Image.new("RGB", (W, H), BG)
    draw = ImageDraw.Draw(img)

    # Estrelas
    rng = random.Random(11)
    for _ in range(140):
        x = rng.randint(0, W)
        y = rng.randint(0, H)
        intensity = rng.choice([50, 80, 120, 180, 230])
        draw.point((x, y), fill=(intensity, intensity, min(255, intensity + 30)))

    # Fontes
    try:
        label_font = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", 11)
        hud_font = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", 12)
        title_font = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", 16)
    except Exception:
        label_font = hud_font = title_font = ImageFont.load_default()

    # Cena: player atacando pirate hostil, com Mule e Albatross neutros
    player = MockShip("Small", "United Humans", W // 2, H // 2,
                      rotation=0, is_player=True, name="Skiff Mk I",
                      model_id="starter_skiff", hp=0.85, shields=0.7)
    pirate = MockShip("Small", "Pirates", W // 2 + 220, H // 2 - 30,
                      rotation=200, name="Wasp Pirate",
                      model_id="wasp_combat", hp=0.4, shields=0.0)
    indep_mule = MockShip("Medium", "Independent", W - 220, H - 170,
                          rotation=-90, name="Mule",
                          model_id="mule_trader", hp=1.0, shields=1.0)
    indep_albatross = MockShip("Small", "Independent", 220, 170,
                               rotation=45, name="Albatross",
                               model_id="albatross_explorer", hp=1.0, shields=1.0)

    ships = [player, pirate, indep_mule, indep_albatross]
    assembler = ProceduralShipAssembler()

    # Renderizar naves
    for ship in ships:
        seed = abs(hash(ship.name)) % 10000
        sprite = assembler.get_ship_image(ship, seed)
        rotated = sprite.rotate(-ship.rotation, resample=Image.BILINEAR, expand=True)
        sx = int(ship.position[0] - rotated.width / 2)
        sy = int(ship.position[1] - rotated.height / 2)
        img.paste(rotated, (sx, sy), rotated)

        # Barra de HP/Shields nos NPCs
        if not ship.is_player:
            cx = int(ship.position[0])
            cy = sy - 6
            bar_w = 36
            # Escudo
            draw.rectangle([cx - bar_w//2, cy - 6, cx + bar_w//2, cy - 3], fill=(30, 30, 50))
            if ship.shields_ratio > 0:
                draw.rectangle([cx - bar_w//2, cy - 6,
                                cx - bar_w//2 + int(bar_w * ship.shields_ratio), cy - 3],
                               fill=(60, 160, 255))
            # HP
            hp_color = (60, 230, 80) if ship.hp_ratio > 0.5 else \
                       ((255, 200, 60) if ship.hp_ratio > 0.25 else (255, 70, 50))
            draw.rectangle([cx - bar_w//2, cy - 2, cx + bar_w//2, cy + 1], fill=(40, 30, 30))
            draw.rectangle([cx - bar_w//2, cy - 2,
                            cx - bar_w//2 + int(bar_w * ship.hp_ratio), cy + 1],
                           fill=hp_color)

            # Label de facção
            label = ship.faction
            tw = draw.textlength(label, font=label_font)
            color = (255, 100, 100) if ship.faction == "Pirates" else (180, 200, 220)
            draw.text((cx - tw / 2, cy - 22), label, fill=color, font=label_font)
        else:
            label = ship.name
            tw = draw.textlength(label, font=label_font)
            cx = int(ship.position[0])
            draw.text((cx - tw / 2, sy - 14), label, fill=(0, 220, 255), font=label_font)

    # ============ PROJÉTEIS em vôo (do player para o pirate) ============
    # Cor kinetic_small
    proj_color = (255, 200, 80)
    # Linha imaginária do player ao pirate
    px, py = player.position
    tx, ty = pirate.position
    # 3 projéteis em distâncias diferentes
    for t in [0.30, 0.55, 0.78]:
        bx = px + (tx - px) * t + random.uniform(-3, 3)
        by = py + (ty - py) * t + random.uniform(-3, 3)
        # Halo
        for r, a in [(7, 50), (5, 110), (3, 200)]:
            overlay = Image.new("RGBA", img.size, (0, 0, 0, 0))
            od = ImageDraw.Draw(overlay)
            od.ellipse([bx - r, by - r, bx + r, by + r], fill=(*proj_color, a))
            img.paste(overlay, (0, 0), overlay)
        # Núcleo branco
        draw.ellipse([bx - 1, by - 1, bx + 1, by + 1], fill=(255, 255, 240))

    # ============ Projétil do pirate de volta pro player ============
    pirate_proj_color = (230, 30, 30)
    # Um projétil na metade do caminho de volta
    bx = tx + (px - tx) * 0.4
    by = ty + (py - ty) * 0.4
    for r, a in [(7, 50), (5, 110), (3, 200)]:
        overlay = Image.new("RGBA", img.size, (0, 0, 0, 0))
        od = ImageDraw.Draw(overlay)
        od.ellipse([bx - r, by - r, bx + r, by + r], fill=(*pirate_proj_color, a))
        img.paste(overlay, (0, 0), overlay)
    draw.ellipse([bx - 1, by - 1, bx + 1, by + 1], fill=(255, 220, 220))

    # ============ Muzzle flash no player (acabou de disparar) ============
    rad = math.radians(player.rotation)
    muzzle_x = player.position[0] + math.cos(rad) * 22
    muzzle_y = player.position[1] + math.sin(rad) * 22
    for r, a in [(8, 80), (6, 140), (3, 220)]:
        overlay = Image.new("RGBA", img.size, (0, 0, 0, 0))
        od = ImageDraw.Draw(overlay)
        od.ellipse([muzzle_x - r, muzzle_y - r, muzzle_x + r, muzzle_y + r],
                   fill=(255, 240, 180, a))
        img.paste(overlay, (0, 0), overlay)

    # ============ Faíscas de impacto no pirate ============
    for _ in range(10):
        ang = random.uniform(0, math.tau)
        d = random.uniform(5, 20)
        sx = pirate.position[0] + math.cos(ang) * d
        sy = pirate.position[1] + math.sin(ang) * d
        color = (255, 240, 200)
        draw.point((sx, sy), fill=color)
        draw.point((sx + 1, sy), fill=color)

    # ============ Anel de escudo (pirate atingido recentemente) ============
    # Mas pirate está com shields=0, então não desenha
    # Vamos pôr no PLAYER, que tem shields 70% e foi atingido pela bala do pirate
    sx, sy = player.position
    radius = 38
    overlay = Image.new("RGBA", img.size, (0, 0, 0, 0))
    od = ImageDraw.Draw(overlay)
    pts = []
    for i in range(6):
        ang = math.radians(60 * i)
        pts.append((sx + math.cos(ang) * radius, sy + math.sin(ang) * radius))
    od.polygon(pts, outline=(80, 180, 255, 130), width=2)
    img.paste(overlay, (0, 0), overlay)

    # ============ HUD ============
    bar_x, bar_y, bar_w, bar_h = 20, 20, 200, 14

    def bar(label, pct, color, y):
        draw.rectangle([bar_x, y, bar_x + bar_w, y + bar_h], fill=(40, 40, 50))
        draw.rectangle([bar_x, y, bar_x + int(bar_w * pct), y + bar_h], fill=color)
        draw.rectangle([bar_x, y, bar_x + bar_w, y + bar_h], outline=(200, 200, 220))
        draw.text((bar_x + bar_w + 10, y), label, fill=(220, 220, 220), font=hud_font)

    bar("SHIELDS", 0.7, (0, 150, 255), bar_y)
    bar("ENERGY", 0.85, (255, 200, 0), bar_y + 24)
    bar("HEAT", 0.4, (255, 70, 30), bar_y + 48)
    draw.text((bar_x, bar_y + 76), "PIPS: W[3] S[2] E[1]", fill=(0, 220, 255), font=hud_font)

    # HUD de combate (canto inferior esquerdo)
    cy = H - 60
    draw.text((20, cy), "HULL: 68/80", fill=(255, 130, 90), font=label_font)
    draw.text((20, cy + 14), "SHIELDS: 70/100", fill=(90, 180, 255), font=label_font)
    # Cooldown da arma (vazio = pronto pra atirar)
    bar_y2 = cy + 32
    draw.rectangle([20, bar_y2, 180, bar_y2 + 8], fill=(40, 40, 50))
    draw.rectangle([20, bar_y2, 100, bar_y2 + 8], fill=(255, 200, 60))
    draw.text((190, bar_y2 - 2), "WEAPON (0.15s)", fill=(200, 220, 240), font=label_font)

    # Controles
    controls = ["W = thrust   A/D = rotate", "ESPAÇO = disparar",
                "1/2/3 = realocar PIP (W/S/E)", "ESC = sair"]
    cy = H - 80
    for line in controls:
        tw = draw.textlength(line, font=label_font)
        draw.text((W - tw - 12, cy), line, fill=(140, 160, 180), font=label_font)
        cy += 14

    draw.text((W // 2 - 130, 8), "Cyberpunk Space RPG", fill=(0, 220, 255), font=title_font)
    draw.text((W - 80, 8), "FPS: 60", fill=(100, 120, 140), font=label_font)

    out_path = "/tmp/space_rpg_sprites/_combat_scene.png"
    img.save(out_path)
    print(f"Cena de combate salva em: {out_path}")
    return img


if __name__ == "__main__":
    os.makedirs("/tmp/space_rpg_sprites", exist_ok=True)
    render_combat_scene()
