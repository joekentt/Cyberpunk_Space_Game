import random
from typing import Dict, Any, List
from core.event_bus import bus
from core.balance import balance

class LootManager:
    """
    Gerencia a geração de recompensas (créditos e itens) após a destruição de alvos.

    Aceita injeção de `rng` (default = módulo random) para testes determinísticos.
    """
    def __init__(self, rng=None):
        self._rng = rng or random
        # Tabelas de loot simplificadas para o MVP
        self.loot_tables = {
            "Small": {"credits": (50, 150), "item_chance": 0.1},
            "Medium": {"credits": (200, 500), "item_chance": 0.25},
            "Large": {"credits": (1000, 2500), "item_chance": 0.5}
        }

    def generate_loot(self, target_class: str) -> Dict[str, Any]:
        """Gera um payload de loot baseado na classe do alvo."""
        table = self.loot_tables.get(target_class, self.loot_tables["Small"])

        credits_won = self._rng.randint(table["credits"][0], table["credits"][1])
        items_won = []

        # Simulação de drop de item
        if self._rng.random() < table["item_chance"]:
            items_won.append("basic_module_scrap") # Exemplo de item

        # Dados de localização (ADR 011): chance data-driven de dropar um item
        # que revela um POI oculto (o main pede o reveal ao ExplorationManager).
        if self._rng.random() < balance.exploration["location_drop_chance"]:
            items_won.append("location_data")

        payload = {
            "credits": credits_won,
            "items": items_won,
            "target_class": target_class
        }

        bus.emit("LOOT_GENERATED", payload)
        return payload

    def on_ship_destroyed(self, data: Dict[str, Any]):
        """Callback para o evento de destruição de nave."""
        target_class = data.get("class", "Small")
        self.generate_loot(target_class)
