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
        )
