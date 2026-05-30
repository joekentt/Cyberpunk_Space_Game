import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from systems.universe_generator import UniverseGenerator

def test_procedural_generation():
    print("--- Iniciando Teste de Geração Procedural (Fase 9) ---")
    
    gen = UniverseGenerator(seed=42)
    
    # 1. Testar Geração de Universo
    sizes = ["Small", "Medium", "Large", "Giant"]
    for size in sizes:
        num = {"Small": 15, "Medium": 25, "Large": 35, "Giant": 50}[size]
        universe = gen.generate_universe(num)
        print(f"Universo {size}: {len(universe)} sistemas gerados.")
        
    # 2. Inspecionar um sistema
    system = gen.generate_system(999)
    print(f"\nInspeção de Sistema Procedural:")
    print(f"  Nome: {system['name']}")
    print(f"  Posição: {system['position']}")
    print(f"  Zona: {system['zone_type']}")
    print(f"  Facções: {system['factions']}")
    print(f"  Estações: {len(system['stations'])}")
    
    # 3. Testar Nomes de NPCs
    print("\nNomes de NPCs Gerados:")
    for _ in range(5):
        print(f"  - {gen.generate_npc_name()}")

    print("\n--- Teste de Geração Procedural Concluído ---")

if __name__ == "__main__":
    test_procedural_generation()
