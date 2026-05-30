from typing import Dict, Any, List
from core.event_bus import bus

class EconomyManager:
    """
    Gerencia créditos do jogador e o mercado básico de módulos.
    """
    def __init__(self, initial_credits: int = 1000):
        self.player_credits = initial_credits
        self.market_inventory: List[Dict[str, Any]] = []

    def add_credits(self, amount: int):
        """Adiciona créditos ao jogador."""
        self.player_credits += amount
        bus.emit("CREDITS_CHANGED", self.player_credits)

    def get_adjusted_price(self, base_price: int, faction_multiplier: float) -> int:
        """Retorna o preço ajustado pela reputação com a facção."""
        return int(base_price * faction_multiplier)

    def buy_module(self, module_data: Dict[str, Any], faction_multiplier: float = 1.0) -> bool:
        """Tenta comprar um módulo do mercado."""
        base_price = module_data.get("price", 0)
        price = self.get_adjusted_price(base_price, faction_multiplier)
        if self.player_credits >= price:
            self.player_credits -= price
            bus.emit("CREDITS_CHANGED", self.player_credits)
            bus.emit("MODULE_PURCHASED", module_data)
            return True
        return False

    def on_loot_collected(self, data: Dict[str, Any]):
        """Callback para quando o jogador coleta loot."""
        credits_won = data.get("credits", 0)
        self.add_credits(credits_won)
