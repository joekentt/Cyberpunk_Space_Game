"""Cura e poções por threshold — aperta as HOTKEYS configuradas no cliente.

O bot não conhece magias do servidor: o usuário monta a rotação nas hotkeys do
próprio cliente (ex.: F1 = cura forte, F2 = poção de vida) e o profile só diz
"qual tecla apertar em qual condição". Isso deixa tudo vocação-agnóstico.

`rules` (do profile.json), avaliadas em ordem, ex.:
    [ {"key": "f1", "stat": "hp",   "below": 40, "cooldown": 1.0},
      {"key": "f3", "stat": "hp",   "below": 80, "cooldown": 1.0},
      {"key": "f2", "stat": "mana", "below": 30, "cooldown": 1.0} ]
"""

import time


class Healer:
    def __init__(self, inputs, rules, time_fn=time.monotonic):
        self.inputs = inputs
        self.rules = rules
        self.time_fn = time_fn
        self._next = {}            # key -> próximo instante liberado

    def tick(self, hp, mana):
        """Avalia as regras e aperta no máximo UMA hotkey por chamada (a
        primeira que casar e estiver fora do cooldown). Curar tem prioridade
        sobre o resto do loop, então é chamado todo frame."""
        now = self.time_fn()
        stats = {"hp": hp, "mana": mana}
        for rule in self.rules:
            val = stats.get(rule["stat"])
            if val is None or val > rule["below"]:
                continue
            key = rule["key"]
            if now < self._next.get(key, 0):
                continue
            self.inputs.press_key(key)
            self._next[key] = now + rule.get("cooldown", 1.0)
            return key
        return None
