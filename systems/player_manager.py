from entities.ship import Ship
from core.event_bus import bus
from core.balance import balance


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
      {"action": "boost"}                       # boost de propulsor (ver try_boost)
      {"action": "set_pips", "system": "weapons"|"shields"|"engines"}
            → realoca 1 pip do sistema com mais pips para o sistema indicado.

    Hierarquia de empuxo (mais forte → mais fraco): frente > ré > strafe lateral.
    Todos escalam com os pips de "engines".

    Boost: ao ativar, injeta empuxo frontal em `thrust_power * force_mult`
    durante `duration` segundos, independente de se o jogador está segurando W.
    O boost só afeta o eixo frontal — ré e strafe são inalterados.
    Números em data/balance.json seção "boost" (ver ADR 007).
    """

    def __init__(self, ship: Ship):
        self.ship = ship
        self.thrust_power = 3000.0                    # motor principal: frente (mais forte)
        self.reverse_power = self.thrust_power * 0.55  # ré: ~55% (mais fraca que a frente)
        self.strafe_power = self.thrust_power * 0.45   # RCS lateral: ~45% (manobra, o mais fraco)
        self.rotation_speed = 220.0                   # graus por segundo (a pleno motor)

        # Distribuição W-S-E (max 6 pips, 0-4 por sistema)
        self.pips = {"weapons": 2, "shields": 2, "engines": 2}
        self.ship.pips = dict(self.pips)

        # Estado de input acumulado durante o frame
        self._input_state = {"thrust": 0.0, "strafe": 0.0, "rotate": 0.0, "shoot": 0.0}

        # Capacitor de boost (recurso próprio, independente de current_energy)
        bp = balance.boost
        self.boost_max: float = bp["max_charge"]
        self.boost_charge: float = self.boost_max
        self._boost_timer: float = 0.0   # tempo de empuxo restante
        self._boost_cd: float = 0.0      # cooldown restante até próxima ativação
        self._sync_boost_to_ship()

        bus.subscribe("PLAYER_INPUT", self._on_input)

    # -- sync HUD --------------------------------------------------

    def _sync_boost_to_ship(self):
        """Espelha estado do capacitor para ship (HUD lê ship.boost_*)."""
        self.ship.boost_charge = self.boost_charge
        self.ship.boost_max = self.boost_max

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
            self._input_state["shoot"] = value
        elif action == "boost":
            self.try_boost()
        elif action == "set_pips":
            self._reallocate_pip(data.get("system"))

    def try_boost(self) -> bool:
        """
        Ativa o boost se possível: sem cooldown, sem boost ativo, carga suficiente.
        Retorna True se ativou, False caso contrário.
        """
        bp = balance.boost
        if self._boost_cd > 0 or self._boost_timer > 0 or self.boost_charge < bp["cost"]:
            return False
        self.boost_charge -= bp["cost"]
        self._boost_timer = bp["duration"]
        self._boost_cd = bp["cooldown"] + bp["duration"]  # cooldown começa após o boost
        bus.emit("BOOST_ACTIVATED", {
            "boost_charge": self.boost_charge,
            "model_id": getattr(self.ship, "model_id", None),
        })
        return True

    def _reallocate_pip(self, target_system: str):
        """Pega 1 pip do sistema com MAIS pips e transfere para o alvo."""
        if target_system not in self.pips:
            return
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

        # Reset de input por frame
        self._input_state["thrust"] = 0.0
        self._input_state["strafe"] = 0.0
        self._input_state["rotate"] = 0.0
        self._input_state["shoot"] = 0.0

        # Boost: empuxo frontal autônomo durante a janela de boost
        if self._boost_timer > 0:
            self._apply_boost_thrust(dt)

        # Timers e recarga do capacitor
        self._boost_timer = max(0.0, self._boost_timer - dt)
        self._boost_cd = max(0.0, self._boost_cd - dt)
        bp = balance.boost
        engine_mod = 0.5 + (self.pips["engines"] / 4.0) * 0.5
        self.boost_charge = min(
            self.boost_max,
            self.boost_charge + bp["recharge_per_s"] * engine_mod * dt,
        )
        self._sync_boost_to_ship()

        # Drag (atrito espacial leve para jogabilidade)
        drag = 0.997
        self.ship.velocity[0] *= drag ** (dt * 60)
        self.ship.velocity[1] *= drag ** (dt * 60)

        # Aplica física
        self.ship.apply_physics(dt)

        bus.emit("PLAYER_MOVED", {
            "pos": list(self.ship.position),
            "rot": self.ship.rotation,
            "vel": list(self.ship.velocity),
        })

    def _apply_boost_thrust(self, dt: float):
        """
        Empuxo de boost frontal — independente do input de W. Só afeta o eixo
        da direção do bico (não afeta ré nem strafe).
        """
        bp = balance.boost
        forward = self.ship.get_forward_vector()
        engine_mod = 0.5 + (self.pips["engines"] / 4.0) * 0.5
        accel = (self.thrust_power * bp["force_mult"] / self.ship.mass) * engine_mod
        self.ship.velocity[0] += forward[0] * accel * dt
        self.ship.velocity[1] += forward[1] * accel * dt
        self.ship.current_heat += 4.0 * dt

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
            power = self.thrust_power
            direction = 1.0
        else:
            power = self.reverse_power
            direction = -1.0
        accel = (power / self.ship.mass) * engine_mod * abs(multiplier)
        self.ship.velocity[0] += forward[0] * direction * accel * dt
        self.ship.velocity[1] += forward[1] * direction * accel * dt
        self.ship.current_heat += 2.0 * dt * abs(multiplier)

    def strafe(self, dt: float, multiplier: float = 1.0):
        """
        Thrusters laterais de manobra (RCS). Deslocam a nave PERPENDICULARMENTE
        ao bico, SEM alterar a rotação. multiplier > 0 = direita, < 0 = esquerda.
        """
        forward = self.ship.get_forward_vector()
        right = (-forward[1], forward[0])
        engine_mod = 0.5 + (self.pips["engines"] / 4.0) * 0.5
        accel = (self.strafe_power / self.ship.mass) * engine_mod * abs(multiplier)
        sign = 1.0 if multiplier > 0 else -1.0
        self.ship.velocity[0] += right[0] * sign * accel * dt
        self.ship.velocity[1] += right[1] * sign * accel * dt
        self.ship.current_heat += 1.0 * dt * abs(multiplier)
