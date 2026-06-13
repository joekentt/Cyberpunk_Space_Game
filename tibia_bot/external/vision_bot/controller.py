"""Loop principal do harness de QA — orquestra captura, leitura e ação.

Prioridade por iteração: ler estado → curar → combater → (se sem inimigo)
andar. Em paralelo coleta as métricas de QA (XP/h, ETA, freeze, anomalias) e
escreve o relatório periodicamente. Pensado para rodar numa thread, comandado
pelo painel (start/pause/stop) e com abort de hardware (failsafe do input).
"""

import os
import time

from .capture import ScreenCapture
from .inputs import Inputs
from .healer import Healer
from .combat import Combat
from .cavebot import CaveBot
from . import state as state_mod
from . import ocr as ocr_mod
from . import qa as qa_mod


class Controller:
    def __init__(self, calib, profile, out_dir="runs", status_cb=None,
                 dry_run=False):
        self.calib = calib
        self.profile = profile
        self.status_cb = status_cb or (lambda s: None)

        self.capture = ScreenCapture()
        self.inputs = Inputs(dry_run=dry_run)
        self.healer = Healer(self.inputs, profile.get("heal_rules", []))
        self.combat = Combat(self.inputs, profile)
        self.cavebot = CaveBot(self.inputs, profile)

        self.xp = qa_mod.XpTracker(window_s=profile.get("xp_window_s", 600))
        self.freeze = qa_mod.FreezeDetector(profile.get("freeze_s", 5.0))
        run_dir = os.path.join(out_dir, time.strftime("%Y%m%d_%H%M%S"))
        self.report = qa_mod.SessionReport(run_dir)
        self.run_dir = run_dir
        self.target_level = profile.get("target_level")

        self.loop_dt = profile.get("loop_dt", 0.15)
        self.xp_every_s = profile.get("xp_read_every_s", 10.0)
        self.report_every_s = profile.get("report_every_s", 30.0)

        self.paused = False
        self.stop = False
        self._dead_fired = False
        self._engage_t = None
        self._last_xp_read = 0
        self._last_report = 0

    # -------- helpers --------

    def _shot(self, tag, img):
        """Salva um screenshot de anomalia e devolve o caminho relativo."""
        try:
            os.makedirs(self.run_dir, exist_ok=True)
            path = os.path.join(self.run_dir, f"{tag}_{int(time.time())}.png")
            img.save(path)
            return path
        except Exception:
            return None

    def _read_xp(self, frame, now):
        if "xp" not in self.calib or now - self._last_xp_read < self.xp_every_s:
            return
        self._last_xp_read = now
        val = ocr_mod.read_int(frame, self.calib["xp"])
        if val is not None:
            self.xp.add_sample(now, val)

    # -------- iteração --------

    def step(self):
        now = time.monotonic()
        frame = self.capture.grab(None)               # tela cheia

        # freeze do mundo: assinatura do viewport
        vp = self.calib.get("viewport")
        sig = self.capture.signature(frame.crop(
            (vp["x"], vp["y"], vp["x"] + vp["w"], vp["y"] + vp["h"]))
            if vp else frame)
        held = self.freeze.update(sig, now)
        if held is not None:
            self.report.anomalies.record(
                "freeze", f"viewport congelado {held:.1f}s",
                self._shot("freeze", frame), now)

        st = state_mod.read_state(frame, self.calib)

        # morte
        if st["hp"] <= 0 and not self._dead_fired:
            self._dead_fired = True
            self.report.anomalies.record(
                "death", "HP zerado", self._shot("death", frame), now)
        elif st["hp"] > 5:
            self._dead_fired = False

        # eventos do log (morte/level/disconnect) via OCR, se a região existir
        if "log" in self.calib:
            for ev in ocr_mod.scan_log_events(frame, self.calib["log"]):
                self.report.anomalies.record(ev, f"log: {ev}", None, now)

        self._read_xp(frame, now)

        # 1) curar  2) combater
        self.healer.tick(st["hp"], st["mana"])
        action = self.combat.tick(st)
        if action == "engage":
            self._engage_t = now
        elif st["has_target"] and self._engage_t is not None:
            latency = (now - self._engage_t) * 1000.0
            st["engage_latency_ms"] = round(latency)
            self._engage_t = None

        # 3) andar só sem inimigo (combate tem prioridade)
        if st["enemies"] == 0 and self.calib.get("minimap"):
            mm = self.calib["minimap"]
            mm_sig = self.capture.signature(frame.crop(
                (mm["x"], mm["y"], mm["x"] + mm["w"], mm["y"] + mm["h"])))
            cv = self.cavebot.tick(mm_sig, now)
            if isinstance(cv, dict):
                self.report.anomalies.record(
                    cv["kind"], cv["msg"], self._shot("stuck", frame), now)

        # métricas
        self.report.sample({
            "t": now, "hp": st["hp"], "mana": st["mana"],
            "enemies": st["enemies"], "xp": self.xp.current_xp(),
        })
        if now - self._last_report >= self.report_every_s:
            self._last_report = now
            self.report.write(self.xp, self.target_level)

        self._emit_status(st, now)

    def _emit_status(self, st, now):
        eta = self.xp.eta_seconds_to_level(self.target_level) \
            if self.target_level else None
        self.status_cb({
            "hp": st["hp"], "mana": st["mana"], "enemies": st["enemies"],
            "xp_h": round(self.xp.xp_per_hour()),
            "eta": qa_mod.fmt_eta(eta) if self.target_level else "-",
            "anomalies": len(self.report.anomalies.events),
            "paused": self.paused,
        })

    def run(self):
        try:
            while not self.stop:
                if self.paused:
                    time.sleep(0.1)
                    continue
                t0 = time.monotonic()
                try:
                    self.step()
                except Exception as e:        # nunca derruba a sessão de QA
                    self.report.anomalies.record("bot_error", repr(e))
                dt = time.monotonic() - t0
                if dt < self.loop_dt:
                    time.sleep(self.loop_dt - dt)
        finally:
            self.report.write(self.xp, self.target_level)
