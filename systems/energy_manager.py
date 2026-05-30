from entities.ship import Ship
from core.event_bus import bus

class EnergyManager:
    """
    Gerencia a distribuição de energia (W-S-E) e a dissipação de calor.
    """
    def __init__(self, ship: Ship):
        self.ship = ship
        self.pips = {"weapons": 2, "shields": 2, "engines": 2}
        
        # Taxas de recarga base
        self.base_recharge = 5.0

    def set_pips(self, weapons: int, shields: int, engines: int):
        """Define a distribuição de pips (máximo total de 6 pips)."""
        total = weapons + shields + engines
        if total <= 6:
            self.pips["weapons"] = weapons
            self.pips["shields"] = shields
            self.pips["engines"] = engines
            bus.emit("PIPS_CHANGED", self.pips)

    def update(self, dt: float):
        """Processa recarga de energia e dissipação de calor."""
        # 1. Dissipação de Calor
        # Quanto mais calor, mais difícil dissipar (simulação simples)
        dissipation = self.ship.heat_dissipation * dt
        self.ship.current_heat = max(0.0, self.ship.current_heat - dissipation)
        
        if self.ship.current_heat > 80.0:
            bus.emit("HEAT_WARNING", self.ship.current_heat)
        
        # 2. Recarga de Escudos (baseado em pips de Shields)
        if self.ship.current_shields < 100.0:
            shield_recharge = (self.base_recharge * (self.pips["shields"] / 2.0)) * dt
            self.ship.current_shields = min(100.0, self.ship.current_shields + shield_recharge)

        # 3. Consumo passivo de energia (simulação)
        # Em um sistema real, isso recarregaria capacitores de armas/motores
        energy_gain = (self.base_recharge * 2) * dt
        self.ship.current_energy = min(self.ship.energy_capacity, self.ship.current_energy + energy_gain)
