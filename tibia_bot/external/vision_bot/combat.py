"""Combate: engaja inimigos e dispara a rotação de ataque por hotkeys.

Estratégia simples e robusta para QA: se há inimigo na battle list e nenhum
alvo marcado, aperta a tecla de "atacar próximo" (padrão do cliente, ex.:
Space). Com alvo marcado, dispara as hotkeys de ataque em rodízio respeitando
um cooldown — de novo, as magias/munição moram nas hotkeys do cliente.
"""

import time


class Combat:
    def __init__(self, inputs, profile, time_fn=time.monotonic):
        self.inputs = inputs
        self.attack_next_key = profile.get("attack_next_key", "space")
        self.attack_keys = profile.get("attack_keys", [])
        self.attack_cooldown = profile.get("attack_cooldown", 2.0)
        self.time_fn = time_fn
        self._next_attack = 0
        self._rot = 0

    def tick(self, st):
        """st = snapshot do vision_bot.state.read_state. Retorna a ação tomada
        ('engage' | 'cast:<key>' | None)."""
        if st["enemies"] <= 0:
            return None

        if not st["has_target"]:
            self.inputs.press_key(self.attack_next_key)
            return "engage"

        now = self.time_fn()
        if self.attack_keys and now >= self._next_attack:
            key = self.attack_keys[self._rot % len(self.attack_keys)]
            self._rot += 1
            self.inputs.press_key(key)
            self._next_attack = now + self.attack_cooldown
            return f"cast:{key}"
        return None
