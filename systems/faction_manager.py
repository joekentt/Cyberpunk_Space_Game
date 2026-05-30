import random
from typing import Dict, Any, List, Set
from core.event_bus import bus

class FactionManager:
    """
    Gerencia a reputação multi-eixo, flags históricas e consequências das ações do jogador.
    """
    def __init__(self):
        # Eixos de Reputação por Facção: {faction_name: {axis_name: value}}
        # Eixos: Trust, Aggression, Economic Value, Political Alignment, Technological Alignment
        self.reputation_axes: Dict[str, Dict[str, int]] = {}
        
        # Flags Históricas (Ações permanentes que marcam o jogador)
        self.historical_flags: Set[str] = set()
        
        # Dados das facções e diplomacia
        self.factions: Dict[str, Dict[str, Any]] = {}
        self.diplomacy: Dict[str, Dict[str, str]] = {}

        # Inscrição em eventos
        bus.subscribe("UPDATE_REPUTATION", self.on_update_reputation)
        bus.subscribe("ADD_HISTORICAL_FLAG", self.add_historical_flag)
        bus.subscribe("TICK", self.on_tick)

    def on_tick(self, dt: float):
        """Lógica de decaimento temporal (ex: agressão diminui com o tempo)."""
        # A cada tick, há uma chance pequena de decaimento para simular passagem de tempo
        # Para o MVP, vamos simplificar o decaimento de Aggression
        for faction in self.reputation_axes:
            agg = self.reputation_axes[faction]["aggression"]
            if agg > 0:
                # Decai 1 ponto a cada 60 segundos (aproximadamente)
                if random.random() < (0.01 * dt): 
                    self.update_axis(faction, "aggression", -1)

    def setup_factions(self, factions_data: List[Dict[str, Any]]):
        """Inicializa as facções com múltiplos eixos."""
        for f in factions_data:
            name = f["name"]
            self.factions[name] = f
            self.diplomacy[name] = f.get("initial_diplomacy", {})
            
            # Inicializa eixos (padrão 0 se não especificado)
            self.reputation_axes[name] = {
                "trust": f.get("initial_trust", 0),
                "aggression": f.get("initial_aggression", 0),
                "economic_value": f.get("initial_economic_value", 0),
                "political_alignment": f.get("initial_political_alignment", 0),
                "technological_alignment": f.get("initial_technological_alignment", 0)
            }

    def on_update_reputation(self, data: Dict[str, Any]):
        """
        data: {
            "faction": str, 
            "impact": Dict[str, int] # Ex: {"trust": 10, "aggression": -5}
        }
        """
        faction_name = data.get("faction")
        impact = data.get("impact")
        
        if faction_name in self.reputation_axes and isinstance(impact, dict):
            for axis, amount in impact.items():
                self.update_axis(faction_name, axis, amount)

    def update_axis(self, faction_name: str, axis: str, amount: int):
        """Atualiza um eixo específico de reputação."""
        if faction_name in self.reputation_axes and axis in self.reputation_axes[faction_name]:
            old_val = self.reputation_axes[faction_name][axis]
            # Limites de -100 a 100
            new_val = max(-100, min(100, old_val + amount))
            self.reputation_axes[faction_name][axis] = new_val
            
            bus.emit("AXIS_CHANGED", {
                "faction": faction_name,
                "axis": axis,
                "amount": amount,
                "total": new_val
            })

    def add_historical_flag(self, flag: str):
        """Adiciona uma marca permanente ao histórico do jogador."""
        if flag not in self.historical_flags:
            self.historical_flags.add(flag)
            bus.emit("FLAG_ADDED", {"flag": flag})

    def get_market_multiplier(self, faction_name: str) -> float:
        """
        Calcula multiplicador de preço baseado em Trust e Economic Value.
        Trust alto e Economic Value alto = Preços melhores (menores para compra).
        """
        axes = self.reputation_axes.get(faction_name, {})
        trust = axes.get("trust", 0)
        econ = axes.get("economic_value", 0)
        
        # Bônus máximo de 20% de desconto
        multiplier = 1.0 - (trust * 0.001) - (econ * 0.001)
        return max(0.8, min(1.5, multiplier))

    def can_dock(self, faction_name: str) -> bool:
        """Verifica permissão de acoplagem baseada em Aggression e Trust."""
        axes = self.reputation_axes.get(faction_name, {})
        if axes.get("aggression", 0) > 50: return False # Muito agressivo
        if axes.get("trust", 0) < -50: return False # Nada confiável
        return True

    def get_save_data(self) -> Dict[str, Any]:
        return {
            "reputation_axes": self.reputation_axes,
            "historical_flags": list(self.historical_flags),
            "diplomacy": self.diplomacy
        }

    def load_save_data(self, data: Dict[str, Any]):
        self.reputation_axes = data.get("reputation_axes", {})
        self.historical_flags = set(data.get("historical_flags", []))
        self.diplomacy = data.get("diplomacy", {})
