from entities.ship import Ship
from core.event_bus import bus


class PlayerManager:
    """
    Gerencia a nave do jogador, processando inputs vindos via EventBus
    (eventos "PLAYER_INPUT") e aplicando movimento, rotação e distribuição
    de energia (sistema W-S-E).

    Inputs aceitos via bus.emit("PLAYER_INPUT", {...}):
      {"action": "thrust",   "value": 1.0}     # throttle: >0 frente, <0 freia/ré
      {"action": "strafe",   "value": 1.0}     # RCS lateral (>0 direita, <0 esquerda)
      {"action": "rotate",   "value":  -1.0}   # rotaciona (esquerda <0, direita >0)
      {"action": "shoot",    "value": 1.0}     # dispara (gancho, sem efeito ainda)
      {"action": "set_pips", "system": "weapons"|"shields"|"engines"}
            → realoca 1 pip do sistema com mais pips para o sistema indicado.

    Hierarquia de empuxo (mais forte → mais fraco): frente > ré > strafe lateral.
    Todos escalam com os pips de "engines".
    """

    def __init__(self, ship: Ship):
        self.ship = ship
        self.thrust_power = 3000.0                    # motor principal: frente (mais forte)
        self.reverse_power = self.thrust_power * 0.55  # ré: ~55% (mais fraca que a frente)
        self.strafe_power = self.thrust_power * 0.45   # RCS lateral: ~45% (manobra, o mais fraco)
        self.rotation_speed = 220.0                   # graus por segundo (a pleno motor)

        # Distribuição W-S-E (max 6 pips, 0-4 por sistema)
        self.pips = {"weapons": 2, "shields": 2, "engines": 2}
        # Espelha para a nave (HUD lê ship.pips)
        self.ship.pips = dict(self.pips)

        # Estado de input acumulado durante o frame
        self._input_state = {"thrust": 0.0, "strafe": 0.0, "rotate": 0.0, "shoot": 0.0}

        # Inscreve no bus
        bus.subscribe("PLAYER_INPUT", self._on_input)

    # -- bus listener --------------------------------------------------

    def _on_input(self, data: dict):
        action = data.get("action")
        value = data.get("value", 0.0)

        if action == "thrust":
            self._input_state["thrust"] = value
        elif action == "strafe":
            self._input_state["strafe"] += value
        elif action == "rotate":
            self._input_state["rotate"] += value
        elif action == "shoot":
            # Disparo é tratado direto pelo CombatManager via bus.
            # Aqui só registramos pra HUD (opcional).
            self._input_state["shoot"] = value
        elif action == "set_pips":
            self._reallocate_pip(data.get("system"))

    def _reallocate_pip(self, target_system: str):
        """Pega 1 pip do sistema com MAIS pips e transfere para o alvo."""
        if target_system not in self.pips:
            return
        # Encontra doador (maior pip count, diferente do alvo)
        donor = max(
            (s for s in self.pips if s != target_system),
            key=lambda s: self.pips[s],
            default=None,
        )
        if donor and self.pips[donor] > 0 and self.pips[target_system] < 4:
            self.pips[donor] -= 1
            self.pips[target_system] += 1
            self.ship.pips = dict(self.pips)
            bus.emit("PIPS_CHANGED", dict(self.pips))

    # -- per-frame update ---------------------------------------------

    def update(self, dt: float):
        # Aplica inputs acumulados
        if self._input_state["rotate"] != 0.0:
            self.rotate(self._input_state["rotate"], dt)
        if self._input_state["thrust"] != 0.0:
            self.accelerate(dt, multiplier=self._input_state["thrust"])
        if self._input_state["strafe"] != 0.0:
            self.strafe(dt, multiplier=self._input_state["strafe"])

        # Reset de input por frame (input é instantâneo, não persiste)
        self._input_state["thrust"] = 0.0
        self._input_state["strafe"] = 0.0
        self._input_state["rotate"] = 0.0
        self._input_state["shoot"] = 0.0

        # Drag (atrito espacial leve para jogabilidade — espaço real não tem)
        drag = 0.997
        self.ship.velocity[0] *= drag ** (dt * 60)
        self.ship.velocity[1] *= drag ** (dt * 60)

        # Aplica física
        self.ship.apply_physics(dt)

        # Emite evento (outros sistemas podem ouvir, ex: câmera, IA)
        bus.emit("PLAYER_MOVED", {
            "pos": list(self.ship.position),
            "rot": self.ship.rotation,
            "vel": list(self.ship.velocity),
        })

    # -- movimento -----------------------------------------------------

    def rotate(self, direction: float, dt: float):
        """Rotaciona a nave. direction>0 = horário, <0 = anti-horário."""
        engine_mod = 0.5 + (self.pips["engines"] / 4.0) * 0.5
        self.ship.rotation += direction * self.rotation_speed * engine_mod * dt

    def accelerate(self, dt: float, multiplier: float = 1.0):
        """
        Throttle estilo Elite Dangerous proporcional aos pips de motor.

        multiplier > 0  → empuxo do motor principal na direção do bico (frente).
        multiplier < 0  → empuxo na direção OPOSTA ao bico, usando a força de ré
                          (mais fraca). Partindo de velocidade frontal positiva,
                          isso primeiro FREIA a nave; ao cruzar o zero (ponto
                          morto), engata a RÉ de fato.
        """
        forward = self.ship.get_forward_vector()
        engine_mod = 0.5 + (self.pips["engines"] / 4.0) * 0.5
        if multiplier >= 0.0:
            power = self.thrust_power      # frente: motor principal (mais forte)
            direction = 1.0
        else:
            power = self.reverse_power     # ré: empuxo traseiro (mais fraco)
            direction = -1.0
        accel = (power / self.ship.mass) * engine_mod * abs(multiplier)
        self.ship.velocity[0] += forward[0] * direction * accel * dt
        self.ship.velocity[1] += forward[1] * direction * accel * dt
        # Aceleração gera calor
        self.ship.current_heat += 2.0 * dt * abs(multiplier)

    def strafe(self, dt: float, multiplier: float = 1.0):
        """
        Thrusters laterais de manobra (RCS). Deslocam a nave PERPENDICULARMENTE
        ao bico, SEM alterar a rotação. multiplier > 0 = direita, < 0 = esquerda.

        É o empuxo mais fraco dos três (não é o motor principal), mas ainda
        escala com os pips de "engines".
        """
        forward = self.ship.get_forward_vector()
        # Perpendicular ao bico (rotação de +90°): (fx, fy) -> (-fy, fx)
        right = (-forward[1], forward[0])
        engine_mod = 0.5 + (self.pips["engines"] / 4.0) * 0.5
        accel = (self.strafe_power / self.ship.mass) * engine_mod * abs(multiplier)
        sign = 1.0 if multiplier > 0 else -1.0
        self.ship.velocity[0] += right[0] * sign * accel * dt
        self.ship.velocity[1] += right[1] * sign * accel * dt
        # Manobra gera menos calor que o motor principal
        self.ship.current_heat += 1.0 * dt * abs(multiplier)
