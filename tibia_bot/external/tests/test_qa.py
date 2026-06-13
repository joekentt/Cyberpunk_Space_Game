"""Testes headless da camada de QA (vision_bot.qa) — lógica pura, sem deps.

Cobre a tabela de XP, taxa/ETA, detector de freeze, log de anomalias e o
relatório de sessão.

Rodar: python tibia_bot/external/tests/test_qa.py
"""

import os
import sys
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, ".."))

from vision_bot import qa

passed = 0


def check(cond, msg):
    global passed
    if not cond:
        print(f"FALHOU: {msg}")
        sys.exit(1)
    passed += 1
    print(f"ok {passed}: {msg}")


# ---- 1. tabela de XP (âncoras conhecidas do Tibia) ----
check(qa.xp_for_level(2) == 100, "xp_for_level(2) == 100")
check(qa.xp_for_level(8) == 4200, "xp_for_level(8) == 4200")
check(qa.xp_for_level(20) == 98800, "xp_for_level(20) == 98800")

# ---- 2. XP/h da sessão ----
t = qa.XpTracker()
t.add_sample(0, 1000)
t.add_sample(1800, 51000)        # +50.000 XP em 0,5 h
check(round(t.session_xp_per_hour()) == 100000, "sessão = 100.000 XP/h")
check(t.current_xp() == 51000, "current_xp acompanha a última amostra")

# ---- 3. ETA até um level alvo ----
eta = t.eta_seconds_to_level(20)
# need = 98800 - 51000 = 47800; a 100.000 XP/h → 1720,8 s
check(abs(eta - 1720.8) < 1.0, f"ETA p/ level 20 ≈ 1721 s (calc {eta:.1f})")
check(t.eta_seconds_to_level(8) == 0.0, "ETA p/ level já alcançado = 0")

# ---- 4. ETA indeterminada quando a XP não sobe ----
flat = qa.XpTracker()
flat.add_sample(0, 5000)
flat.add_sample(600, 5000)
check(flat.eta_seconds_to_level(50) is None, "XP parada → ETA None")
check(qa.fmt_eta(None).startswith("indeterminado"), "fmt_eta(None) legível")
check(qa.fmt_eta(3725) == "1h02m", "fmt_eta formata h/m")

# ---- 5. detector de freeze (borda de subida) ----
fd = qa.FreezeDetector(threshold_s=5.0)
check(fd.update("A", now=0) is None, "1º frame não dispara")
check(fd.update("A", now=2) is None, "2 s parado ainda não dispara")
fired = fd.update("A", now=6)
check(fired is not None and fired >= 5, f"freeze dispara aos 6 s (held {fired})")
check(fd.update("A", now=7) is None, "não redispara enquanto continua parado")
check(fd.update("B", now=8) is None, "frame muda → rearma sem evento")
check(fd.update("B", now=14) is not None, "novo freeze dispara depois de rearmar")

# ---- 6. log de anomalias ----
log = qa.AnomalyLog()
log.record("stuck", "parado no mesmo SQM por 30 s", now=1)
log.record("death", "personagem morreu", now=2)
log.record("stuck", "travou de novo", now=3)
check(log.summary() == {"stuck": 2, "death": 1}, "summary agrega por tipo")

# ---- 7. relatório de sessão escrito em disco ----
with tempfile.TemporaryDirectory() as d:
    rep = qa.SessionReport(out_dir=d)
    rep.t0 = 0
    rep.sample({"t": 0, "hp": 100, "mana": 80, "xp": 1000, "enemies": 0})
    rep.sample({"t": 1800, "hp": 90, "mana": 50, "xp": 51000, "enemies": 2})
    rep.anomalies.record("freeze", "tela congelou 6 s", now=900)
    out = rep.write(t, target_level=20)
    check(out["xp_per_hour_session"] == 100000, "relatório traz XP/h da sessão")
    check(out["eta_to_target_human"] != "", "relatório traz ETA legível")
    check(out["anomaly_count"] == 1, "relatório conta anomalias")
    check(os.path.exists(os.path.join(d, "report.json")), "report.json escrito")
    check(os.path.exists(os.path.join(d, "series.csv")), "series.csv escrito")

print(f"\ntodos os {passed} checks passaram")
