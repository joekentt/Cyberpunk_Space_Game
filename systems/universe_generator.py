import random
import math
from typing import List, Dict, Any

class UniverseGenerator:
    """
    Gera sistemas estelares, planetas e estações de forma procedural.
    """
    def __init__(self, seed: Any = None):
        self.seed = seed
        if seed:
            random.seed(seed)
            
        self.system_prefixes = ["Neo", "Cyber", "Nova", "Zenith", "Void", "Astra", "Glitch"]
        self.system_suffixes = ["Prime", "Sector", "Void", "Station", "Nexus", "Core"]
        
        self.npc_names = ["Jax", "Kira", "Vane", "Zed", "Nyx", "Rico", "Sora", "Bane"]
        self.npc_titles = ["The Ghost", "Ace", "Drifter", "Merc", "Shadow", "Reaper"]

    def generate_npc_name(self) -> str:
        """Gera um nome procedural para um piloto NPC."""
        if random.random() < 0.3:
            return f"{random.choice(self.npc_names)} '{random.choice(self.npc_titles)}'"
        return f"{random.choice(self.npc_names)} {random.randint(100, 999)}"

    def generate_universe(self, num_systems: int) -> List[Dict[str, Any]]:
        universe = []
        for i in range(num_systems):
            system = self.generate_system(i)
            universe.append(system)
        return universe

    def generate_system(self, system_id: int) -> Dict[str, Any]:
        name = f"{random.choice(self.system_prefixes)} {random.choice(self.system_suffixes)} {random.randint(10, 99)}"
        
        # Coordenadas galácticas (escala macro)
        pos_x = random.uniform(-5000, 5000)
        pos_y = random.uniform(-5000, 5000)
        
        # Tipo de zona baseado na distância do centro (0,0)
        dist_from_center = math.sqrt(pos_x**2 + pos_y**2)
        if dist_from_center < 1500:
            zone_type = "SAFE"
        elif dist_from_center < 3500:
            zone_type = "FRONTIER"
        else:
            zone_type = "NEUTRAL"

        return {
            "id": system_id,
            "name": name,
            "position": [pos_x, pos_y],
            "zone_type": zone_type,
            "factions": self._assign_factions(zone_type),
            "stations": self._generate_stations(random.randint(1, 3)),
            "asteroid_fields": random.randint(0, 5)
        }

    def _assign_factions(self, zone_type: str) -> List[str]:
        if zone_type == "SAFE":
            return ["United Humans"]
        elif zone_type == "FRONTIER":
            return random.sample(["United Humans", "Marth", "Orcs"], 2)
        else:
            return ["Pirates", "Independent"]

    def _generate_stations(self, count: int) -> List[Dict[str, Any]]:
        stations = []
        for _ in range(count):
            stations.append({
                "name": f"Outpost {random.randint(100, 999)}",
                "type": random.choice(["TRADE", "MILITARY", "MINING"]),
                "services": ["REPAIR", "MARKET", "MISSIONS"]
            })
        return stations
