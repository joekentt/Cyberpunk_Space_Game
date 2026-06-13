"""OCR de XP/level e eventos do log. pytesseract importado preguiçosamente.

Usado pela camada de QA para ler a XP atual (janela de skills) e varrer o log
do jogo atrás de eventos ("you are dead", "you advanced", desconexão). É a
parte mais sensível a fonte/escala — por isso fica isolada e tolerante a falha
(devolve None quando não consegue ler).
"""


def _engine():
    import pytesseract       # lazy: só na máquina do usuário (+ Tesseract)
    return pytesseract


def _crop(img, region):
    if region is None:
        return img
    x, y, w, h = region["x"], region["y"], region["w"], region["h"]
    return img.crop((x, y, x + w, y + h))


def read_text(img, region=None, lang="eng"):
    try:
        return _engine().image_to_string(_crop(img, region), lang=lang)
    except Exception:
        return ""


def read_int(img, region=None):
    """Lê um inteiro de uma região (ex.: XP). None se não houver dígitos."""
    digits = "".join(c for c in read_text(img, region) if c.isdigit())
    return int(digits) if digits else None


# eventos de interesse no log do jogo (substring, minúsculo)
LOG_EVENTS = {
    "death": ["you are dead", "voce esta morto"],
    "advance": ["you advanced", "voce avancou"],
    "disconnect": ["connection lost", "conexao perdida"],
}


def scan_log_events(img, region, lang="eng"):
    """Retorna os tipos de evento detectados no texto do log da tela."""
    text = read_text(img, region, lang).lower()
    found = []
    for kind, needles in LOG_EVENTS.items():
        if any(n in text for n in needles):
            found.append(kind)
    return found
