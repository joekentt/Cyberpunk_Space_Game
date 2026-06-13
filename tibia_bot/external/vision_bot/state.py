"""Leitura de estado pela interface — só Pillow + stdlib (testável headless).

Tudo opera sobre uma `PIL.Image` já capturada (o frame da janela do cliente) e
regiões calibradas em coordenadas RELATIVAS a esse frame. Sem leitura de
memória: HP/mana saem da razão de preenchimento das barras; inimigos e alvo
saem da battle list.

Uma "região" é um dict {"x","y","w","h"} (pixels dentro do frame).
"""

from PIL import Image


# --------------------------------------------------------------------------
# helpers de cor
# --------------------------------------------------------------------------

def _is_filled_default(px):
    """Pixel 'preenchido' de uma barra: claro e/ou saturado (não é o fundo
    escuro da barra vazia nem a borda cinza). Robusto à troca de cor da barra
    de HP (verde → amarelo → vermelho conforme a vida cai)."""
    mx, mn = max(px[0], px[1], px[2]), min(px[0], px[1], px[2])
    return mx > 80 and (mx - mn) > 30


def _reddish(px):
    return px[0] > 120 and px[0] - px[1] > 60 and px[0] - px[2] > 60


def _crop(img, region):
    x, y, w, h = region["x"], region["y"], region["w"], region["h"]
    return img.convert("RGB").crop((x, y, x + w, y + h))


# --------------------------------------------------------------------------
# barras de HP / mana
# --------------------------------------------------------------------------

def bar_fill_ratio(img, region, is_filled=_is_filled_default):
    """Razão 0..1 de quanto a barra está cheia (colunas preenchidas / largura).

    Amostra algumas linhas no meio da barra (evita as bordas superior/inferior)
    e usa a contagem máxima — o trecho cheio fica contíguo à esquerda, mas
    contar o total de colunas preenchidas é robusto a antialias."""
    crop = _crop(img, region)
    w, h = crop.size
    if w == 0 or h == 0:
        return 0.0
    px = crop.load()
    sample_rows = [max(0, min(h - 1, int(h * f))) for f in (0.35, 0.5, 0.65)]
    best = 0
    for ry in sample_rows:
        cnt = sum(1 for cx in range(w) if is_filled(px[cx, ry]))
        best = max(best, cnt)
    return best / w


def read_hp_percent(img, calib):
    return round(bar_fill_ratio(img, calib["hp_bar"]) * 100)


def read_mana_percent(img, calib):
    return round(bar_fill_ratio(img, calib["mana_bar"]) * 100)


# --------------------------------------------------------------------------
# battle list (inimigos visíveis + alvo)
# --------------------------------------------------------------------------

def _non_bg_fraction(crop, bg=(34, 34, 34), tol=24):
    """Fração de pixels que NÃO são o fundo da UI (linha com conteúdo)."""
    px = crop.load()
    w, h = crop.size
    total = w * h
    if total == 0:
        return 0.0
    cnt = 0
    for yy in range(h):
        for xx in range(w):
            p = px[xx, yy]
            if (abs(p[0] - bg[0]) > tol or abs(p[1] - bg[1]) > tol
                    or abs(p[2] - bg[2]) > tol):
                cnt += 1
    return cnt / total


def count_battle_entries(img, region, row_height,
                         bg=(34, 34, 34), occupied_frac=0.05):
    """Conta entradas ocupadas na battle list (contíguas a partir do topo).

    Cada criatura visível ocupa uma linha de `row_height` px; linhas vazias têm
    só o fundo da UI. Para no primeiro vazio (o cliente preenche de cima p/
    baixo)."""
    crop = _crop(img, region)
    w, h = crop.size
    rows = h // row_height if row_height > 0 else 0
    count = 0
    for r in range(rows):
        band = crop.crop((0, r * row_height, w, (r + 1) * row_height))
        if _non_bg_fraction(band, bg) >= occupied_frac:
            count += 1
        else:
            break
    return count


def target_row(img, region, row_height, red_frac=0.06):
    """Índice da linha-alvo (moldura vermelha de 'atacando') ou -1.

    Procura a linha com mais pixels avermelhados acima de um limiar — a moldura
    de alvo é uma borda vermelha em volta da entrada."""
    crop = _crop(img, region)
    w, h = crop.size
    rows = h // row_height if row_height > 0 else 0
    best_idx, best_score = -1, red_frac
    for r in range(rows):
        band = crop.crop((0, r * row_height, w, (r + 1) * row_height))
        px = band.load()
        bw, bh = band.size
        if bw * bh == 0:
            continue
        red = sum(1 for yy in range(bh) for xx in range(bw)
                  if _reddish(px[xx, yy]))
        score = red / (bw * bh)
        if score > best_score:
            best_idx, best_score = r, score
    return best_idx


def read_state(img, calib):
    """Snapshot completo do estado lido da tela."""
    bl = calib["battle_list"]
    rh = bl.get("row_height", 22)
    entries = count_battle_entries(img, bl, rh)
    tgt = target_row(img, bl, rh)
    return {
        "hp": read_hp_percent(img, calib),
        "mana": read_mana_percent(img, calib),
        "enemies": entries,
        "has_target": tgt >= 0,
        "target_row": tgt,
    }
