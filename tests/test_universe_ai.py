"""
Teste de Universo e IA de NPC (API atual).

Exercita o fluxo VIVO do NPCManager: NPCManager(universe) + register_npc(),
dirigido por chamadas diretas a update(dt) (espelha test_combat.py e evita que
asserts sejam engolidos pelo try/except do EventBus.emit).

Cobre:
  1. Detecção: NPC hostil (Pirates) em IDLE detecta o player (United Humans)
     dentro do detection_range e entra em CHASE, perseguindo-o (distância cai).
  2. Aproximação até ATTACK quando entra no attack_range.
  3. FLEE: com flee_shield_threshold elevado e escudos baixos, o NPC foge
     (distância volta a crescer).

Headless, sem pygame. Roda direto: python tests/test_universe_ai.py
"""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.event_bus import bus
from systems.universe_manager import UniverseManager
from systems.npc_manager import NPCManager, NPCBehavior
from entities.ship import Ship


def _dist(a, b):
    return ((a.position[0] - b.position[0]) ** 2 +
            (a.position[1] - b.position[1]) ** 2) ** 0.5


def test_universe_ai():
    print("--- Iniciando Teste de Universo e IA ---")

    # Bus é singleton global: limpar listeners de testes anteriores.
    bus._listeners.clear()

    universe = UniverseManager()
    npc_mgr = NPCManager(universe)

    # Player (alvo imóvel) — facção hostil aos Pirates.
    player_template = Ship(
        id="player", name="Skiff", ship_class="Small", model_id="starter_skiff",
        mass=120, energy_capacity=100, heat_dissipation=8,
        max_hp=80, current_hp=80, max_shields=100, current_shields=100,
        is_player=True, faction="United Humans",
    )
    pid = universe.spawn_ship(player_template, [0.0, 0.0])
    player = universe.entities[pid]

    # NPC pirata em IDLE, dentro do detection_range (~707px < 1000).
    pirate_template = Ship(
        id="pirate", name="Wasp Pirate", ship_class="Small", model_id="wasp_combat",
        mass=100, energy_capacity=100, heat_dissipation=5,
        max_hp=70, current_hp=70, max_shields=80, current_shields=80,
        faction="Pirates",
    )
    npc_id = universe.spawn_ship(pirate_template, [500.0, 500.0])
    npc = universe.entities[npc_id]
    npc_mgr.register_npc(npc_id, NPCBehavior.IDLE)

    dist0 = _dist(player, npc)
    print(f"\nDistância inicial: {dist0:.1f} | Estado: {npc_mgr.npc_ships[npc_id]}")
    assert npc_mgr.npc_ships[npc_id] == NPCBehavior.IDLE

    # 1+2. Perseguição: simula 5s; player parado, NPC deve aproximar.
    dt = 1 / 60.0
    for i in range(300):
        npc_mgr.update(dt)
        universe.update(dt)
        if i % 60 == 0:
            print(f"T={i*dt:.1f}s | Estado: {npc_mgr.npc_ships[npc_id]} | Dist: {_dist(player, npc):.1f}")

    dist_chase = _dist(player, npc)
    state_chase = npc_mgr.npc_ships[npc_id]
    print(f"\nApós perseguição: Estado={state_chase} | Dist={dist_chase:.1f}")
    assert state_chase in (NPCBehavior.CHASE, NPCBehavior.ATTACK), \
        f"NPC hostil deveria estar perseguindo/atacando, está {state_chase}"
    assert dist_chase < dist0, "NPC não se aproximou do player"

    # 3. FLEE: eleva o threshold de fuga e zera escudos -> deve fugir.
    npc_mgr.flee_shield_threshold = 50.0
    npc.current_shields = 10.0
    # Garante que está em ATTACK (handler que checa o threshold de fuga).
    npc_mgr.npc_ships[npc_id] = NPCBehavior.ATTACK
    npc_mgr.update(dt)  # transição ATTACK -> FLEE
    assert npc_mgr.npc_ships[npc_id] == NPCBehavior.FLEE, \
        "NPC com escudos baixos deveria entrar em FLEE"
    print(f"\nEscudos baixos -> Estado: {npc_mgr.npc_ships[npc_id]}")

    # Zera o momento acumulado na perseguição para isolar o vetor de fuga
    # (a IA não aplica drag; do contrário o NPC coasta em direção ao alvo).
    npc.velocity = [0.0, 0.0]
    dist_flee_start = _dist(player, npc)
    for _ in range(300):  # 5s fugindo (precisa girar ~180° antes de acelerar)
        npc_mgr.update(dt)
        universe.update(dt)
    dist_flee_end = _dist(player, npc)
    print(f"Distância durante fuga: {dist_flee_start:.1f} -> {dist_flee_end:.1f}")
    assert dist_flee_end > dist_flee_start, "NPC em FLEE deveria se afastar do player"

    print("\nTeste de Universo e IA: OK")


if __name__ == "__main__":
    test_universe_ai()
