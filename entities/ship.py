from dataclasses import dataclass, field
from typing import List, Dict, Any
from entities.module import Module
import math

@dataclass
class Ship:
    """
    Representa uma nave no universo.
    Gerencia estado físico, módulos e atributos base.
    """
    id: str
    name: str
    ship_class: str  # Small, Medium, Large (categoria de tamanho)
    mass: float
    energy_capacity: float
    heat_dissipation: float

    # Identificador do MODELO específico da nave (define a silhueta visual).
    # Ex: "starter_skiff", "viper", "anaconda". Se None, cai no ship_class.
    # Vários modelos podem compartilhar a mesma ship_class.
    model_id: str = None
    
    # Estado Físico
    position: List[float] = field(default_factory=lambda: [0.0, 0.0])
    velocity: List[float] = field(default_factory=lambda: [0.0, 0.0])
    rotation: float = 0.0  # Em graus
    
    # Estado de Recursos
    current_energy: float = 0.0
    current_heat: float = 0.0
    current_shields: float = 100.0
    max_shields: float = 100.0
    current_hp: float = 100.0       # HP do casco (estrutura)
    max_hp: float = 100.0
    
    # Módulos
    modules: List[Module] = field(default_factory=list)

    # Hardpoints declarados (de ships.json). Ex:
    # {"weapon_small": 2, "weapon_medium": 0, "weapon_large": 0, "utility": 1}
    # Define o poder de fogo da nave (ver CombatManager.hardpoint_firepower).
    hardpoints: Dict[str, int] = field(default_factory=dict)

    # Atributos de Identidade
    is_player: bool = False
    faction: str = "Independent"
    
    # Economia (geralmente só relevante para o player)
    credits: int = 0

    def __post_init__(self):
        self.current_energy = self.energy_capacity

    def apply_physics(self, dt: float):
        """Aplica movimento vetorial baseado na velocidade atual."""
        self.position[0] += self.velocity[0] * dt
        self.position[1] += self.velocity[1] * dt

    def get_forward_vector(self):
        """Retorna o vetor unitário para a frente da nave baseado na rotação."""
        rad = math.radians(self.rotation)
        return [math.cos(rad), math.sin(rad)]

    @classmethod
    def from_dict(cls, data: Dict[str, Any]):
        stats = data.get("base_stats", {})
        hp = stats.get("hull_hp", 100.0)
        shields = stats.get("shields_max", 100.0)
        return cls(
            id=data["id"],
            name=data["name"],
            ship_class=data["class"],
            mass=stats.get("mass", 100.0),
            energy_capacity=stats.get("energy_capacity", 100.0),
            heat_dissipation=stats.get("heat_dissipation", 5.0),
            model_id=data.get("model_id", data.get("id")),
            current_hp=hp,
            max_hp=hp,
            current_shields=shields,
            max_shields=shields,
            hardpoints=dict(data.get("hardpoints", {})),
        )

    # -- Serialização do ESTADO VIVO (runtime) ---------------------------
    # Distinto de from_dict: este caminho captura/restaura o estado de uma
    # nave já viva no universo (posição, velocidade, HP atual, etc.), e não
    # o template do catálogo ships.json (que usa a chave "base_stats").
    #
    # NOTA DE DESIGN: `credits` NÃO é incluído aqui de propósito. Os créditos
    # têm uma única fonte de verdade no save (campo top-level do payload),
    # então o serializer os trata separadamente para evitar duplicação.

    def to_save_dict(self) -> Dict[str, Any]:
        """Serializa o estado VIVO da nave (não o template do catálogo)."""
        return {
            "model_id": self.model_id,
            "name": self.name,
            "ship_class": self.ship_class,
            "mass": self.mass,
            "energy_capacity": self.energy_capacity,
            "heat_dissipation": self.heat_dissipation,
            "hardpoints": dict(self.hardpoints),
            "position": list(self.position),
            "velocity": list(self.velocity),
            "rotation": self.rotation,
            "current_hp": self.current_hp,
            "max_hp": self.max_hp,
            "current_shields": self.current_shields,
            "max_shields": self.max_shields,
            "current_heat": self.current_heat,
            "faction": self.faction,
            "is_player": self.is_player,
        }

    @classmethod
    def from_save_dict(cls, data: Dict[str, Any], ship_id: str = "player"):
        """Reconstrói uma nave a partir do estado vivo serializado."""
        ship = cls(
            id=ship_id,
            name=data["name"],
            ship_class=data["ship_class"],
            mass=data["mass"],
            energy_capacity=data["energy_capacity"],
            heat_dissipation=data["heat_dissipation"],
            model_id=data.get("model_id"),
            position=list(data.get("position", [0.0, 0.0])),
            velocity=list(data.get("velocity", [0.0, 0.0])),
            rotation=data.get("rotation", 0.0),
            current_shields=data.get("current_shields", 100.0),
            max_shields=data.get("max_shields", 100.0),
            current_hp=data.get("current_hp", 100.0),
            max_hp=data.get("max_hp", 100.0),
            current_heat=data.get("current_heat", 0.0),
            hardpoints=dict(data.get("hardpoints", {})),
            is_player=data.get("is_player", False),
            faction=data.get("faction", "Independent"),
        )
        return ship
