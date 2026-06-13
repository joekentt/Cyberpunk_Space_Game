"""Calibração: o usuário marca as regiões da tela UMA vez (overlay tkinter).

Sem pixels hardcoded — as coords (absolutas de tela) de cada região vão para um
JSON. Resolve a fragilidade de resolução/tema do reconhecimento por imagem.
Rode sempre que mudar resolução, tema da UI ou layout do cliente.
"""

import json
import os

# regiões obrigatórias + opcionais. (nome, descrição, obrigatória?)
REGIONS = [
    ("viewport", "área do jogo (mundo) — usada p/ detectar tela congelada", True),
    ("hp_bar", "barra de vida (só a barra, sem o número)", True),
    ("mana_bar", "barra de mana (só a barra)", True),
    ("battle_list", "lista de criaturas (todas as linhas visíveis)", True),
    ("minimap", "minimapa (área clicável p/ andar)", True),
    ("xp", "número da XP na janela de skills (p/ XP/h e ETA)", False),
    ("log", "área de texto do log do jogo (eventos p/ QA)", False),
]


def _select_region(prompt):
    """Abre um overlay translúcido em tela cheia; o usuário arrasta um retângulo
    e solta. Devolve {'x','y','w','h'} em coords de tela, ou None se cancelar."""
    import tkinter as tk

    root = tk.Tk()
    root.attributes("-fullscreen", True)
    try:
        root.attributes("-alpha", 0.3)
    except tk.TclError:
        pass
    root.configure(bg="black")
    canvas = tk.Canvas(root, cursor="cross", bg="gray11", highlightthickness=0)
    canvas.pack(fill="both", expand=True)
    canvas.create_text(root.winfo_screenwidth() // 2, 40, fill="white",
                       font=("Arial", 18),
                       text=f"{prompt}\n(arraste e solte — ESC cancela)")

    box = {"x0": 0, "y0": 0, "x1": 0, "y1": 0, "rect": None, "ok": False}

    def on_press(e):
        box["x0"], box["y0"] = e.x, e.y

    def on_drag(e):
        if box["rect"]:
            canvas.delete(box["rect"])
        box["rect"] = canvas.create_rectangle(
            box["x0"], box["y0"], e.x, e.y, outline="red", width=2)

    def on_release(e):
        box["x1"], box["y1"], box["ok"] = e.x, e.y, True
        root.quit()

    canvas.bind("<ButtonPress-1>", on_press)
    canvas.bind("<B1-Motion>", on_drag)
    canvas.bind("<ButtonRelease-1>", on_release)
    root.bind("<Escape>", lambda e: root.quit())
    root.mainloop()
    root.destroy()

    if not box["ok"]:
        return None
    x, y = min(box["x0"], box["x1"]), min(box["y0"], box["y1"])
    w, h = abs(box["x1"] - box["x0"]), abs(box["y1"] - box["y0"])
    if w < 3 or h < 3:
        return None
    return {"x": x, "y": y, "w": w, "h": h}


def run_calibration(path="config/calibration.json"):
    calib = {}
    for name, desc, required in REGIONS:
        region = _select_region(f"Selecione: {name} — {desc}")
        if region is None:
            if required:
                print(f"[calibração] '{name}' é obrigatória; tente de novo.")
                region = _select_region(f"Selecione: {name} — {desc}")
                if region is None:
                    raise SystemExit("calibração cancelada")
            else:
                continue
        calib[name] = region

    calib.setdefault("battle_list", {})["row_height"] = \
        calib["battle_list"].get("row_height", 22)

    os.makedirs(os.path.dirname(path) or ".", exist_ok=True)
    with open(path, "w") as f:
        json.dump(calib, f, indent=2)
    print(f"[calibração] salva em {path}")
    return calib


if __name__ == "__main__":
    run_calibration()
