"""Camada de QA — o entregável principal: métricas, extrapolação e anomalias.

Lógica pura (stdlib): mede a curva de XP da sessão, extrapola o tempo até um
level alvo na dificuldade natural do servidor, detecta tela congelada
(freeze/lag) e registra anomalias/bugs com timestamp para revisão humana.
Não depende de visão — recebe valores já lidos pelo `state`/`ocr`.
"""

import csv
import json
import os
import time


# --------------------------------------------------------------------------
# tabela de XP do Tibia (mapa global / oficial-like)
# --------------------------------------------------------------------------

def xp_for_level(level):
    """XP acumulada para ATINGIR `level` (fórmula clássica do Tibia).

    Âncoras conhecidas: level 2 = 100, level 8 = 4200."""
    L = int(level)
    return (50 * (L ** 3 - 6 * L ** 2 + 17 * L - 12)) // 3


# --------------------------------------------------------------------------
# rastreador de XP / ETA
# --------------------------------------------------------------------------

class XpTracker:
    """Acumula amostras (tempo, xp) e estima XP/h e tempo até um level alvo.

    Usa uma janela deslizante para a taxa instantânea (resiste a picos) e a
    média total da sessão para a projeção de longo prazo."""

    def __init__(self, window_s=600.0):
        self.window_s = window_s
        self.samples = []          # [(t, xp)]
        self.start = None

    def add_sample(self, t, xp):
        if self.start is None:
            self.start = (t, xp)
        self.samples.append((t, xp))
        # poda amostras fora da janela (mantém ao menos 2)
        cutoff = t - self.window_s
        while len(self.samples) > 2 and self.samples[1][0] < cutoff:
            self.samples.pop(0)

    def _rate(self, pair_a, pair_b):
        dt = pair_b[0] - pair_a[0]
        if dt <= 0:
            return 0.0
        return (pair_b[1] - pair_a[1]) / dt * 3600.0

    def xp_per_hour(self):
        """Taxa na janela deslizante (XP/h)."""
        if len(self.samples) < 2:
            return 0.0
        return self._rate(self.samples[0], self.samples[-1])

    def session_xp_per_hour(self):
        """Taxa média desde o início da sessão (XP/h)."""
        if self.start is None or not self.samples:
            return 0.0
        return self._rate(self.start, self.samples[-1])

    def current_xp(self):
        return self.samples[-1][1] if self.samples else (
            self.start[1] if self.start else 0)

    def eta_seconds_to_level(self, target_level, use_session=True):
        """Segundos estimados até `target_level` na taxa atual (None se parado
        ou já alcançado)."""
        need = xp_for_level(target_level) - self.current_xp()
        if need <= 0:
            return 0.0
        rate = self.session_xp_per_hour() if use_session else self.xp_per_hour()
        if rate <= 0:
            return None
        return need / rate * 3600.0


def fmt_eta(seconds):
    if seconds is None:
        return "indeterminado (sem XP recente)"
    if seconds <= 0:
        return "alcançado"
    h = int(seconds // 3600)
    m = int((seconds % 3600) // 60)
    return f"{h}h{m:02d}m"


# --------------------------------------------------------------------------
# detector de tela congelada (freeze / lag de servidor ou cliente)
# --------------------------------------------------------------------------

class FreezeDetector:
    """Sinaliza quando o frame não muda por mais de `threshold_s`.

    Alimentado com uma assinatura do frame (hash/checksum). Borda de subida:
    emite UM evento ao cruzar o limiar; rearma quando o frame volta a mudar."""

    def __init__(self, threshold_s=5.0):
        self.threshold_s = threshold_s
        self._last_sig = None
        self._last_change = None
        self._fired = False

    def update(self, signature, now=None):
        """Retorna a duração do freeze (s) se um NOVO freeze acabou de cruzar o
        limiar; senão None."""
        now = time.time() if now is None else now
        if self._last_sig is None:
            self._last_sig, self._last_change = signature, now
            return None
        if signature != self._last_sig:
            self._last_sig, self._last_change, self._fired = signature, now, False
            return None
        held = now - self._last_change
        if held >= self.threshold_s and not self._fired:
            self._fired = True
            return held
        return None


# --------------------------------------------------------------------------
# log de anomalias / bugs
# --------------------------------------------------------------------------

class AnomalyLog:
    """Registra eventos suspeitos (travado, morte, disconnect, freeze, etc.)
    com timestamp e caminho opcional de screenshot. Sinaliza para revisão
    humana — não é um oráculo de bugs."""

    def __init__(self):
        self.events = []           # [{t, kind, msg, shot}]

    def record(self, kind, msg, shot=None, now=None):
        self.events.append({
            "t": time.time() if now is None else now,
            "kind": kind, "msg": msg, "shot": shot,
        })

    def summary(self):
        counts = {}
        for e in self.events:
            counts[e["kind"]] = counts.get(e["kind"], 0) + 1
        return counts


# --------------------------------------------------------------------------
# relatório de sessão
# --------------------------------------------------------------------------

class SessionReport:
    """Agrega séries temporais + métricas + anomalias e escreve em disco."""

    def __init__(self, out_dir):
        self.out_dir = out_dir
        self.t0 = time.time()
        self.series = []           # [{t, hp, mana, xp, enemies}]
        self.anomalies = AnomalyLog()

    def sample(self, row):
        row = dict(row)
        row.setdefault("t", time.time())
        self.series.append(row)

    def build(self, xp_tracker, target_level=None):
        elapsed = (self.series[-1]["t"] - self.t0) if self.series else 0.0
        report = {
            "elapsed_s": round(elapsed, 1),
            "samples": len(self.series),
            "xp_start": xp_tracker.start[1] if xp_tracker.start else None,
            "xp_now": xp_tracker.current_xp(),
            "xp_per_hour_session": round(xp_tracker.session_xp_per_hour()),
            "xp_per_hour_window": round(xp_tracker.xp_per_hour()),
            "anomalies": self.anomalies.summary(),
            "anomaly_count": len(self.anomalies.events),
        }
        if target_level is not None:
            eta = xp_tracker.eta_seconds_to_level(target_level)
            report["target_level"] = target_level
            report["eta_to_target_s"] = None if eta is None else round(eta)
            report["eta_to_target_human"] = fmt_eta(eta)
        return report

    def write(self, xp_tracker, target_level=None):
        os.makedirs(self.out_dir, exist_ok=True)
        report = self.build(xp_tracker, target_level)
        with open(os.path.join(self.out_dir, "report.json"), "w") as f:
            json.dump({"report": report, "anomalies": self.anomalies.events},
                      f, indent=2)
        if self.series:
            keys = sorted({k for row in self.series for k in row})
            with open(os.path.join(self.out_dir, "series.csv"), "w",
                      newline="") as f:
                w = csv.DictWriter(f, fieldnames=keys)
                w.writeheader()
                w.writerows(self.series)
        return report
