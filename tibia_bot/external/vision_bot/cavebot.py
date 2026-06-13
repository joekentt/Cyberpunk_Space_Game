"""Caçada por waypoints clicados no MINIMAPA — sem arquivos de mapa.

Cada waypoint é um ponto de clique (coords de tela ABSOLUTAS) sobre o minimapa.
Clicar no minimapa usa o pathfinding do próprio cliente no mapa global, então o
bot não precisa conhecer o mapa. O avanço é guiado pela assinatura do minimapa:
ele muda enquanto o personagem anda e estabiliza ao chegar.

Detecção de "travado": se após clicar o minimapa não muda por `stuck_s`, emite
uma anomalia (para o relatório de QA) e reclica.
"""

import time


class CaveBot:
    def __init__(self, inputs, profile, time_fn=time.monotonic):
        self.inputs = inputs
        self.waypoints = list(profile.get("waypoints", []))   # [{"x","y"}]
        self.arrive_stable_s = profile.get("arrive_stable_s", 0.8)
        self.stuck_s = profile.get("stuck_s", 8.0)
        self.reclick_s = profile.get("reclick_s", 2.5)
        self.time_fn = time_fn
        self.idx = 0
        self._sig = None
        self._sig_t = 0
        self._last_click = None
        self._moved = False
        self._stuck_fired = False

    def add_waypoint(self, x, y):
        self.waypoints.append({"x": x, "y": y})

    def clear(self):
        self.waypoints = []
        self.idx = 0
        self._last_click = None

    def _click(self, wp, now):
        self.inputs.click(wp["x"], wp["y"])
        self._last_click = now
        self._moved = False
        self._sig_t = now

    def tick(self, minimap_sig, now=None):
        """Avança a rota. Retorna None, uma string de ação ('walk'/'advance'/
        'reclick') ou um dict de anomalia {'kind','msg'}."""
        if not self.waypoints:
            return None
        now = self.time_fn() if now is None else now

        if self._sig is None:
            self._sig, self._sig_t = minimap_sig, now
        elif minimap_sig != self._sig:
            self._sig, self._sig_t = minimap_sig, now
            self._moved = True
            self._stuck_fired = False

        wp = self.waypoints[self.idx]

        if self._last_click is None:
            self._click(wp, now)
            return "walk"

        stable = now - self._sig_t
        # chegou: mexeu desde o clique e o minimapa estabilizou
        if self._moved and stable >= self.arrive_stable_s:
            self.idx = (self.idx + 1) % len(self.waypoints)
            self._click(self.waypoints[self.idx], now)
            return "advance"

        # travado: tempo demais sem mexer desde o clique
        if not self._moved and (now - self._last_click) >= self.stuck_s:
            event = None
            if not self._stuck_fired:
                self._stuck_fired = True
                event = {"kind": "stuck",
                         "msg": f"sem mover após clicar no waypoint {self.idx}"}
            self._click(wp, now)
            return event or "reclick"

        # reclica periodicamente enquanto caminha (Tibia exige reenviar destino)
        if (now - self._last_click) >= self.reclick_s:
            self._click(wp, now)
            return "reclick"

        return None
