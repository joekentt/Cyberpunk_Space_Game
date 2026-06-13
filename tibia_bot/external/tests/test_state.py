"""Testes headless da leitura de estado (vision_bot.state).

Gera imagens sintéticas com Pillow (barras com preenchimento conhecido, battle
list com linhas ocupadas/vazias, moldura de alvo) e valida que o `state` lê os
valores certos — sem precisar do cliente, numpy ou opencv.

Rodar: python tibia_bot/external/tests/test_state.py
"""

import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, ".."))

from PIL import Image
from vision_bot import state

passed = 0


def check(cond, msg):
    global passed
    if not cond:
        print(f"FALHOU: {msg}")
        sys.exit(1)
    passed += 1
    print(f"ok {passed}: {msg}")


GREEN = (0, 180, 0)
RED = (200, 30, 30)
BLUE = (40, 80, 200)
DARK = (30, 30, 30)
UIBG = (34, 34, 34)


def make_bar(width, height, fill_ratio, color=GREEN, bg=DARK):
    img = Image.new("RGB", (width, height), bg)
    px = img.load()
    fill = int(width * fill_ratio)
    for x in range(fill):
        for y in range(height):
            px[x, y] = color
    return img


# ---- 1. barra de HP 37% ----
img = make_bar(100, 10, 0.37)
ratio = state.bar_fill_ratio(img, {"x": 0, "y": 0, "w": 100, "h": 10})
check(abs(ratio * 100 - 37) <= 2, f"barra 37% lida como {round(ratio*100)}%")

# ---- 2. barra cheia e vazia ----
full = state.bar_fill_ratio(make_bar(100, 10, 1.0),
                            {"x": 0, "y": 0, "w": 100, "h": 10})
empty = state.bar_fill_ratio(make_bar(100, 10, 0.0),
                             {"x": 0, "y": 0, "w": 100, "h": 10})
check(round(full * 100) >= 98, "barra cheia ≈ 100%")
check(round(empty * 100) <= 2, "barra vazia ≈ 0%")

# ---- 3. troca de cor da barra (HP baixo fica vermelho) não engana ----
red_bar = state.bar_fill_ratio(make_bar(100, 10, 0.20, color=RED),
                               {"x": 0, "y": 0, "w": 100, "h": 10})
check(abs(red_bar * 100 - 20) <= 2, "barra vermelha (HP baixo) 20% lida certo")

# ---- 4. mana azul ----
mana_bar = state.bar_fill_ratio(make_bar(100, 10, 0.60, color=BLUE),
                                {"x": 0, "y": 0, "w": 100, "h": 10})
check(abs(mana_bar * 100 - 60) <= 2, "barra de mana azul 60% lida certo")

# ---- 5. battle list: 3 ocupadas + 2 vazias = 3 ----
ROW = 22
bl = Image.new("RGB", (120, ROW * 5), UIBG)
px = bl.load()
for r in range(3):                       # 3 primeiras linhas com "conteúdo"
    for x in range(4, 116):
        for y in range(r * ROW + 3, r * ROW + ROW - 3):
            px[x, y] = (180, 180, 180) if (x + y) % 2 else (90, 60, 40)
region = {"x": 0, "y": 0, "w": 120, "h": ROW * 5, "row_height": ROW}
n = state.count_battle_entries(bl, region, ROW)
check(n == 3, f"battle list conta 3 inimigos (leu {n})")

# ---- 6. battle list vazia = 0 ----
empty_bl = Image.new("RGB", (120, ROW * 5), UIBG)
check(state.count_battle_entries(empty_bl, region, ROW) == 0,
      "battle list vazia conta 0")

# ---- 7. moldura de alvo na 2ª entrada ----
for x in range(4, 116):                  # borda vermelha em volta da linha 1
    px[x, 1 * ROW + 1] = RED
    px[x, 2 * ROW - 2] = RED
for y in range(1 * ROW, 2 * ROW):
    px[4, y] = RED
    px[115, y] = RED
tgt = state.target_row(bl, region, ROW)
check(tgt == 1, f"alvo detectado na linha 1 (leu {tgt})")

# ---- 8. sem alvo = -1 ----
check(state.target_row(empty_bl, region, ROW) == -1,
      "sem moldura vermelha → target_row = -1")

# ---- 9. read_state integra tudo ----
calib = {
    "hp_bar": {"x": 0, "y": 0, "w": 100, "h": 10},
    "mana_bar": {"x": 0, "y": 0, "w": 100, "h": 10},
    "battle_list": region,
}
# compõe um frame: usa a battle list como base e finge barras cheias no canto
frame = bl.copy()
fpx = frame.load()
for x in range(100):                     # HP 100% nas 10 primeiras linhas
    for y in range(10):
        fpx[x, y] = GREEN
st = state.read_state(frame, calib)
check(st["enemies"] == 3 and st["has_target"] and st["hp"] >= 98,
      f"read_state: {st}")

print(f"\ntodos os {passed} checks passaram")
