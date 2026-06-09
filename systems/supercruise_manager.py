"""
SupercruiseManager — lógica pura (sem pygame) da viagem rápida intra-setor.

Ver ADR 010. Este módulo só faz contas: dado o player (uma Ship com
`position`, `velocity`, `rotation`, `get_forward_vector`, `apply_physics`), a
lista de massas (estações com `.position` e `.docking_radius`) e `dt`, acelera a
nave ao longo da proa, integra a posição e decide se deve dar **drop** ao se
aproximar de massa. Não conhece `game_state` nem pygame — o `main_pygame`
decide as transições com base no dict retornado por `step()`.

Regra de segurança central: o ponto de drop fica a `exit_offset` da massa, na
linha player→massa, e `exit_offset` é sempre maior que o `docking_radius` da
estação — assim o player nunca acopla sozinho ao sair do supercruise.
"""
import math
from typing import Any, Dict, List, Optional


class SupercruiseManager:
    def __init__(self, balance_section: Dict[str, Any]):
        sc = balance_section
        self.speed_mult: float = sc["speed_mult"]
        self.max_speed: float = sc["max_speed"]
        self.accel: float = sc["accel"]
        self.spool_up_s: float = sc["spool_up_s"]
        self.drop_radius: float = sc["drop_radius"]
        self.exit_offset: float = sc["exit_offset"]
        self.min_entry_distance: float = sc["min_entry_distance"]

    # ------------------------------------------------------------------
    @staticmethod
    def _dist(a, b) -> float:
        return math.hypot(a[0] - b[0], a[1] - b[1])

    def can_enter(self, player_pos, masses) -> bool:
        """
        False se houver qualquer massa dentro de `min_entry_distance` (perto
        demais para engatar com segurança). True caso contrário.
        """
        for m in masses:
            if self._dist(player_pos, m.position) < self.min_entry_distance:
                return False
        return True

    def _nearest(self, player_pos, masses):
        """(massa, distância) da massa mais próxima, ou (None, inf)."""
        nearest = None
        nd = float("inf")
        for m in masses:
            d = self._dist(player_pos, m.position)
            if d < nd:
                nearest = m
                nd = d
        return nearest, nd

    def _safe_drop_pos(self, player_pos, mass) -> List[float]:
        """
        Ponto seguro de saída: a `exit_offset` da massa, na linha massa→player
        (do lado de onde a nave veio). Garantidamente FORA do docking_radius.
        """
        mx, my = mass.position[0], mass.position[1]
        dx = player_pos[0] - mx
        dy = player_pos[1] - my
        d = math.hypot(dx, dy)
        if d <= 1e-9:
            # Degenerado: player exatamente em cima da massa. Empurra para +X.
            return [mx + self.exit_offset, my]
        ux, uy = dx / d, dy / d
        return [mx + ux * self.exit_offset, my + uy * self.exit_offset]

    def step(self, player, masses, dt: float) -> Dict[str, Any]:
        """
        Avança um frame de supercruise.

        - Acelera o player ao longo da proa até `max_speed`.
        - Integra a posição (via `player.apply_physics`).
        - Se alguma massa entrar em `drop_radius`, sinaliza `drop=True` e devolve
          o `drop_pos` seguro (não muta o estado — quem reposiciona é o caller).

        Retorna:
          {"drop": bool, "drop_pos": [x,y]|None, "nearest": mass|None,
           "distance": float, "speed": float}
        """
        forward = player.get_forward_vector()

        # Acelera ao longo da proa.
        vx = player.velocity[0] + forward[0] * self.accel * dt
        vy = player.velocity[1] + forward[1] * self.accel * dt

        # Clampa no máximo de supercruise (módulo).
        speed = math.hypot(vx, vy)
        if speed > self.max_speed:
            scale = self.max_speed / speed
            vx *= scale
            vy *= scale
            speed = self.max_speed

        player.velocity[0] = vx
        player.velocity[1] = vy
        player.apply_physics(dt)

        nearest, nd = self._nearest(player.position, masses)

        if nearest is not None and nd <= self.drop_radius:
            return {
                "drop": True,
                "drop_pos": self._safe_drop_pos(player.position, nearest),
                "nearest": nearest,
                "distance": nd,
                "speed": speed,
            }

        return {
            "drop": False,
            "drop_pos": None,
            "nearest": nearest,
            "distance": nd,
            "speed": speed,
        }
