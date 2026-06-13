"""Painel de controle (tkinter): start/pause/stop, calibrar, gravar waypoints
e status ao vivo (HP/mana/inimigos, XP/h, ETA, nº de anomalias).

O controlador roda numa thread separada; o painel só comanda e mostra status.
Gravar waypoint = captura a posição atual do mouse sobre o minimapa (posicione
o cursor onde quer andar e clique no botão / aperte F9).
"""

import json
import os
import threading

from .controller import Controller
from . import calibrate as calib_mod


class Panel:
    def __init__(self, calib_path="config/calibration.json",
                 profile_path="config/profile.json"):
        self.calib_path = calib_path
        self.profile_path = profile_path
        self.controller = None
        self.thread = None
        self._status = {}

    # -------- arquivos --------

    def _load(self, path, default):
        try:
            with open(path) as f:
                return json.load(f)
        except Exception:
            return default

    def _mouse_pos(self):
        try:
            import pyautogui
            return pyautogui.position()
        except Exception:
            return (0, 0)

    # -------- ciclo do bot --------

    def start(self):
        if self.thread and self.thread.is_alive():
            return
        calib = self._load(self.calib_path, None)
        if not calib:
            self._set_msg("Calibre primeiro (botão Calibrar).")
            return
        profile = self._load(self.profile_path, {})
        self.controller = Controller(
            calib, profile, status_cb=self._on_status)
        self.thread = threading.Thread(target=self.controller.run, daemon=True)
        self.thread.start()
        self._set_msg("Rodando. (mouse no canto sup-esq = ABORT)")

    def toggle_pause(self):
        if self.controller:
            self.controller.paused = not self.controller.paused

    def stop(self):
        if self.controller:
            self.controller.stop = True
            self._set_msg(f"Parado. Relatório em {self.controller.run_dir}")

    def record_waypoint(self):
        x, y = self._mouse_pos()
        profile = self._load(self.profile_path, {})
        profile.setdefault("waypoints", []).append({"x": int(x), "y": int(y)})
        os.makedirs(os.path.dirname(self.profile_path) or ".", exist_ok=True)
        with open(self.profile_path, "w") as f:
            json.dump(profile, f, indent=2)
        if self.controller:
            self.controller.cavebot.add_waypoint(int(x), int(y))
        self._set_msg(f"Waypoint gravado em ({x},{y}). Total: "
                      f"{len(profile['waypoints'])}")

    def calibrate(self):
        calib_mod.run_calibration(self.calib_path)
        self._set_msg("Calibração concluída.")

    # -------- UI --------

    def _on_status(self, s):
        self._status = s

    def _set_msg(self, msg):
        self._msg = msg
        if hasattr(self, "msg_var"):
            self.msg_var.set(msg)

    def run(self):
        import tkinter as tk

        root = tk.Tk()
        root.title("EXP Bot — QA Harness")
        root.geometry("360x300")

        self.msg_var = tk.StringVar(value="Pronto. Calibre e configure o profile.")
        self.stat_var = tk.StringVar(value="—")

        def btn(text, cmd):
            tk.Button(root, text=text, command=cmd, width=34).pack(pady=2)

        btn("① Calibrar regiões da tela", self.calibrate)
        btn("② Gravar waypoint (mouse no minimapa)", self.record_waypoint)
        btn("▶ Iniciar", self.start)
        btn("⏸ Pausar / retomar", self.toggle_pause)
        btn("■ Parar (salva relatório)", self.stop)

        tk.Label(root, textvariable=self.stat_var, justify="left",
                 font=("Consolas", 10)).pack(pady=6)
        tk.Label(root, textvariable=self.msg_var, wraplength=340,
                 fg="navy").pack(pady=4)

        root.bind("<F9>", lambda e: self.record_waypoint())

        def refresh():
            s = self._status
            if s:
                self.stat_var.set(
                    f"HP {s['hp']:>3}%  Mana {s['mana']:>3}%  "
                    f"inimigos {s['enemies']}\n"
                    f"XP/h {s['xp_h']:>8}   ETA {s['eta']}\n"
                    f"anomalias {s['anomalies']}"
                    f"{'   [PAUSADO]' if s['paused'] else ''}")
            root.after(300, refresh)

        refresh()
        root.mainloop()
