"""
Preview visual dos jatos de thruster (motor principal, ré e strafe).

Não é um teste de lógica — gera um PNG mostrando a Skiff com cada tipo de
jato ativo, para conferir o feedback visual proporcional à hierarquia de
força (frente forte > ré média > strafe fraco).

Usa o VFXGenerator REAL para gerar e envelhecer as partículas (mesma fórmula
do jogo), depois desenha as partículas vivas com Pillow. A geometria de
origem/direção dos jatos espelha main_pygame._rcs_vfx.
"""
import os
import sys
import math

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from PIL import Image, ImageDraw, ImageFont
from visual_engine.vfx_generator import VFXGenerator
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


# ---- geometria dos jatos (espelha main_pygame._rcs_vfx / _handle_input) ----

def emit_jet(vfx, kind, pos, rotation, color, direction=0.0):
    rad = math.radians(rotation)
    forward = (math.cos(rad), math.sin(rad))
    right = (-forward[1], forward[0])
    px, py = pos

    if kind == "forward":
        vfx.create_engine_trail(tuple(pos), rotation, color)
    elif kind == "reverse":
        nose = 16
        origin = (px + forward[0] * nose, py + forward[1] * nose)
        jet_dir = math.degrees(math.atan2(forward[1], forward[0]))
        vfx.create_rcs_puff(origin, jet_dir, color, strength="reverse")
    else:  # strafe
        side = 12
        if direction > 0:   # E: jato sai da esquerda
            origin = (px - right[0] * side, py - right[1] * side)
            jet = (-right[0], -right[1])
        else:               # Q: jato sai da direita
            origin = (px + right[0] * side, py + right[1] * side)
            jet = (right[0], right[1])
        jet_dir = math.degrees(math.atan2(jet[1], jet[0]))
        vfx.create_rcs_puff(origin, jet_dir, color, strength="strafe")


def simulate_particles(kind, rotation, color, direction=0.0, frames=26, speed=0.0):
    """
    Segura a tecla por `frames` frames com a nave EM MOVIMENTO (velocidade
    `speed` na direção do empuxo). Como no jogo a câmera segue a nave, o
    rastro fica para trás dela — é isso que dá o comprimento visível.
    Retorna (partículas_vivas, posição_final_da_nave).
    """
    vfx = VFXGenerator()
    vfx.particles.clear()
    dt = 1 / 60

    rad = math.radians(rotation)
    forward = (math.cos(rad), math.sin(rad))
    right = (-forward[1], forward[0])
    if kind == "forward":
        vdir = forward
    elif kind == "reverse":
        vdir = (-forward[0], -forward[1])
    else:  # strafe: a nave acelera para o lado do empuxo
        vdir = right if direction > 0 else (-right[0], -right[1])

    pos = [0.0, 0.0]
    for _ in range(frames):
        pos[0] += vdir[0] * speed * dt
        pos[1] += vdir[1] * speed * dt
        emit_jet(vfx, kind, pos, rotation, color, direction)
        vfx.update(dt)
    live = [p for p in vfx.particles if p.life > 0]
    return live, (pos[0], pos[1])


def draw_particles(draw_img, particles, scale, origin_px):
    """Desenha as partículas com glow (overlay RGBA), na escala do painel."""
    ox, oy = origin_px
    for p in particles:
        alpha = max(0, min(255, int((p.life / p.max_life) * 255)))
        x = ox + p.pos[0] * scale
        y = oy + p.pos[1] * scale
        r = max(1, int(p.size * scale))
        col = tuple(p.color[:3])
        # glow
        draw_img.ellipse([x - r * 2, y - r * 2, x + r * 2, y + r * 2],
                         fill=(*col, max(20, alpha // 4)))
        # core
        draw_img.ellipse([x - r, y - r, x + r, y + r], fill=(*col, alpha))


def render_panel(canvas, draw, font, label, sublabel, kind, direction,
                 panel_x, panel_y, panel_w, panel_h):
    """Renderiza um painel: fundo, nave, jato e legenda."""
    # Moldura do painel
    draw.rectangle([panel_x, panel_y, panel_x + panel_w, panel_y + panel_h],
                   fill=(12, 14, 24), outline=(40, 60, 80))

    # Simulação em coordenadas nativas (escala 1x), com a nave em movimento.
    scale = 3
    rotation = -90  # bico apontando para cima na imagem

    palette = PaletteManager().get_palette("United Humans")
    accent = palette["accent"][:3]

    # Velocidades de preview proporcionais à hierarquia (frente > ré > strafe).
    speed = {"forward": 150.0, "reverse": 85.0, "strafe": 65.0}[kind]
    particles, ship_pos = simulate_particles(
        kind, rotation, accent, direction=direction, speed=speed)

    # A posição final da nave fica no centro do painel; as partículas (em
    # coords de mundo) são deslocadas pelo mesmo offset → rastro atrás da nave.
    origin_px = (panel_w / 2 - ship_pos[0] * scale,
                 panel_h / 2 - ship_pos[1] * scale)

    # Overlay RGBA para as partículas (com alpha)
    overlay = Image.new("RGBA", (panel_w, panel_h), (0, 0, 0, 0))
    odraw = ImageDraw.Draw(overlay)
    draw_particles(odraw, particles, scale, origin_px)

    # Nave (PIL), upscale x scale, rotacionada
    assembler = ProceduralShipAssembler()
    ship = MockShip("Small", "United Humans", 0, 0, rotation=rotation,
                    is_player=True, model_id="starter_skiff")
    sprite = assembler.get_ship_image(ship, seed=1)
    big = sprite.resize((sprite.width * scale, sprite.height * scale), Image.NEAREST)
    rotated = big.rotate(-rotation, resample=Image.BILINEAR, expand=True)

    ship_layer = Image.new("RGBA", (panel_w, panel_h), (0, 0, 0, 0))
    bx = int(panel_w / 2 - rotated.width / 2)
    by = int(panel_h / 2 - rotated.height / 2)
    ship_layer.paste(rotated, (bx, by), rotated)

    # Compõe: partículas atrás da nave (escape sai por trás), nave por cima
    panel_img = Image.new("RGBA", (panel_w, panel_h), (0, 0, 0, 0))
    panel_img = Image.alpha_composite(panel_img, overlay)
    panel_img = Image.alpha_composite(panel_img, ship_layer)
    canvas.paste(panel_img, (panel_x, panel_y), panel_img)

    # Legenda
    draw.text((panel_x + 10, panel_y + 8), label, fill=(0, 220, 255), font=font[0])
    draw.text((panel_x + 10, panel_y + 30), sublabel, fill=(170, 190, 210), font=font[1])
    draw.text((panel_x + 10, panel_y + panel_h - 22),
              f"{len(particles)} partículas vivas", fill=(120, 140, 160), font=font[1])


def main():
    os.makedirs("/tmp/space_rpg_sprites", exist_ok=True)

    try:
        f_title = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", 28)
        f_label = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", 15)
        f_sub = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", 12)
    except Exception:
        f_title = f_label = f_sub = ImageFont.load_default()

    panel_w, panel_h = 300, 300
    margin = 16
    cols, rows = 2, 2
    W = margin * (cols + 1) + panel_w * cols
    H = 70 + margin * (rows + 1) + panel_h * rows

    canvas = Image.new("RGBA", (W, H), (8, 8, 18, 255))
    draw = ImageDraw.Draw(canvas)
    draw.text((margin, 18), "Feedback visual dos thrusters — Skiff Mk I",
              fill=(0, 220, 255), font=f_title)

    panels = [
        ("MOTOR PRINCIPAL (W)", "Rastro grande — escape pela traseira",
         "forward", 0.0),
        ("RÉ / FREIO (S)", "Jato médio — RCS de proa empurra pra trás",
         "reverse", 0.0),
        ("STRAFE ESQUERDA (Q)", "Jato fraco — sai pela lateral direita",
         "strafe", -1.0),
        ("STRAFE DIREITA (E)", "Jato fraco — sai pela lateral esquerda",
         "strafe", 1.0),
    ]

    y0 = 70
    for i, (label, sub, kind, direction) in enumerate(panels):
        r, c = divmod(i, cols)
        px = margin + c * (panel_w + margin)
        py = y0 + margin + r * (panel_h + margin)
        render_panel(canvas, draw, (f_label, f_sub), label, sub, kind, direction,
                     px, py, panel_w, panel_h)

    out = "/tmp/space_rpg_sprites/_thrusters_preview.png"
    canvas.convert("RGB").save(out)
    print(f"Preview salvo em: {out}")
    return out


if __name__ == "__main__":
    main()
