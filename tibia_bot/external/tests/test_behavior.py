"""Testes headless de comportamento (healer, combat, cavebot).

Usam Inputs(dry_run=True) — que registra as ações sem tocar teclado/mouse — e
um relógio injetado, então a lógica de threshold/cooldown/rodízio/anti-stuck é
verificada sem cliente nem libs de input.

Rodar: python tibia_bot/external/tests/test_behavior.py
"""

import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, ".."))

from vision_bot.inputs import Inputs
from vision_bot.healer import Healer
from vision_bot.combat import Combat
from vision_bot.cavebot import CaveBot

passed = 0


def check(cond, msg):
    global passed
    if not cond:
        print(f"FALHOU: {msg}")
        sys.exit(1)
    passed += 1
    print(f"ok {passed}: {msg}")


clock = [0.0]
tf = lambda: clock[0]

# ============================ HEALER ============================
rules = [
    {"key": "f1", "stat": "hp", "below": 40, "cooldown": 1.0},
    {"key": "f3", "stat": "hp", "below": 80, "cooldown": 1.0},
    {"key": "f2", "stat": "mana", "below": 30, "cooldown": 1.0},
]
inp = Inputs(dry_run=True)
h = Healer(inp, rules, time_fn=tf)

check(h.tick(100, 100) is None, "healer não age com HP/mana cheios")
check(h.tick(70, 100) == "f3", "HP 70% → cura leve (f3)")
check(h.tick(70, 100) is None, "cooldown bloqueia segunda cura no mesmo instante")
clock[0] = 1.0
check(h.tick(70, 100) == "f3", "após cooldown, cura de novo")
check(h.tick(30, 100) == "f1", "HP 30% → cura forte (f1) tem prioridade")
check(h.tick(100, 20) == "f2", "mana 20% → poção de mana (f2)")

# ============================ COMBAT ============================
clock[0] = 0.0
inp2 = Inputs(dry_run=True)
profile = {"attack_next_key": "space", "attack_keys": ["f5", "f6"],
           "attack_cooldown": 2.0}
c = Combat(inp2, profile, time_fn=tf)

check(c.tick({"enemies": 0, "has_target": False}) is None,
      "sem inimigo → combate não age")
check(c.tick({"enemies": 2, "has_target": False}) == "engage",
      "inimigo sem alvo → engaja (atacar próximo)")
check(c.tick({"enemies": 2, "has_target": True}) == "cast:f5",
      "com alvo → primeira hotkey de ataque")
check(c.tick({"enemies": 2, "has_target": True}) is None,
      "cooldown de ataque respeitado")
clock[0] = 2.0
check(c.tick({"enemies": 2, "has_target": True}) == "cast:f6",
      "rodízio para a segunda hotkey de ataque")

# ============================ CAVEBOT ============================
clock[0] = 0.0
inp3 = Inputs(dry_run=True)
cav = CaveBot(inp3, {"waypoints": [{"x": 10, "y": 10}, {"x": 20, "y": 20}],
                     "arrive_stable_s": 0.5, "stuck_s": 3.0, "reclick_s": 2.5},
              time_fn=tf)

check(cav.tick("a", now=0.0) == "walk", "1º tick clica o waypoint atual")
check(cav.tick("b", now=0.6) is None, "minimapa mudou (andando) → aguarda")
adv = cav.tick("b", now=1.2)
check(adv == "advance" and cav.idx == 1, "minimapa estabilizou → avança waypoint")
check(("click", (20, 20, "left")) in inp3.log, "avançar clicou o próximo waypoint")

# travado: minimapa não muda por stuck_s após o clique do waypoint 1
check(cav.tick("b", now=1.5) is None, "ainda dentro da tolerância de travado")
ev = cav.tick("b", now=4.5)
check(isinstance(ev, dict) and ev["kind"] == "stuck",
      "sem mover por stuck_s → anomalia 'stuck' para o relatório de QA")

print(f"\ntodos os {passed} checks passaram")
