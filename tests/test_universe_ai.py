"""
Teste de universo + FSM da IA de NPC (headless, sem pygame).

Reescrito contra a API atual do NPCManager. A API antiga
(`NPCManager(npc_ship, target=player)`, `npc_ai.state`, FLEE com threshold 20)
não existe mais: hoje o manager gerencia TODOS os NPCs via
`NPCManager(universe)`, registra com `register_npc(ship_id, estado)`, acha o
player sozinho (flag `is_player`) e guarda o estado em `npc_ships[ship_id]`.

Cobre a intenção original — perseguição e transições da FSM — mais um caso de
não-hostil que permanece IDLE. FLEE por escudo está DESLIGADO no balance atual
(`flee_shield_threshold = 0`, ver ADR 004: piratas Tier 1 lutam até o fim),
então aqui forçamos o threshold só nesta instância para validar a transição.
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.event_bus import bus
from systems.universe_manager import UniverseManager
from systems.npc_manager import NPCManager, NPCBehavior
from entities.ship import Ship


def _ship(name, faction, model_id="wasp_combat", ship_class="Small",
          is_player=False, hp=70, shields=80, mass=100):
    return Ship(
        id=name,
        name=name,
        ship_class=ship_class,
        model_id=model_id,
        mass=mass,
        energy_capacity=100,
        heat_dissipation=5,
        max_hp=hp, current_hp=hp,
        max_shields=shields, current_shields=shields,
        is_player=is_player,
        faction=faction,
    )


def main():
    print("=" * 60)
    print("Teste de Universo e IA (FSM)")
    print("=" * 60)

    bus._listeners.clear()

    universe = UniverseManager()
    npc_mgr = NPCManager(universe)

    # Player (United Humans) e um pirata dentro do detection_range
    pid = universe.spawn_ship(_ship("player", "United Humans", is_player=True), [0, 0])
    pirate_id = universe.spawn_ship(_ship("pirate", "Pirates"), [500, 0])
    # NPC não-hostil (Independent) também próximo
    indep_id = universe.spawn_ship(
        _ship("indep", "Independent", model_id="mule_trader",
              ship_class="Medium", hp=200, shields=150, mass=350),
        [0, 500],
    )

    player = universe.entities[pid]
    pirate = universe.entities[pirate_id]

    npc_mgr.register_npc(pirate_id, NPCBehavior.IDLE)
    npc_mgr.register_npc(indep_id, NPCBehavior.IDLE)

    dist0 = ((pirate.position[0] - player.position[0]) ** 2 +
             (pirate.position[1] - player.position[1]) ** 2) ** 0.5
    assert dist0 < npc_mgr.detection_range, dist0

    # ------------------------------------------------------------------
    # 1) IDLE → CHASE: o pirata detecta o player hostil e persegue
    # ------------------------------------------------------------------
    print("\n[1] IDLE → CHASE (detecção de hostil)")
    assert npc_mgr.npc_ships[pirate_id] == NPCBehavior.IDLE
    dt = 1 / 60.0
    # Um único tick já basta para detectar dentro do range
    npc_mgr.update(dt)
    universe.update(dt)
    assert npc_mgr.npc_ships[pirate_id] == NPCBehavior.CHASE, npc_mgr.npc_ships[pirate_id]
    assert npc_mgr.targets[pirate_id] == pid
    print("  ✓ pirata entrou em CHASE e mira o player")

    # ------------------------------------------------------------------
    # 2) CHASE → ATTACK: ao fechar distância (< attack_range)
    # ------------------------------------------------------------------
    print("\n[2] CHASE → ATTACK (fechou distância)")
    reached_attack = False
    for _ in range(600):  # até 10 s
        npc_mgr.update(dt)
        universe.update(dt)
        if npc_mgr.npc_ships[pirate_id] == NPCBehavior.ATTACK:
            reached_attack = True
            break
    assert reached_attack, "pirata não chegou a ATTACK"
    d = ((pirate.position[0] - player.position[0]) ** 2 +
         (pirate.position[1] - player.position[1]) ** 2) ** 0.5
    assert d < npc_mgr.attack_range + 1.0, d
    print(f"  ✓ pirata em ATTACK a {d:.0f}px (attack_range={npc_mgr.attack_range:.0f})")

    # ------------------------------------------------------------------
    # 3) Não-hostil permanece IDLE
    # ------------------------------------------------------------------
    print("\n[3] NPC não-hostil (Independent) fica em IDLE")
    assert npc_mgr.npc_ships[indep_id] == NPCBehavior.IDLE, npc_mgr.npc_ships[indep_id]
    print("  ✓ Independent nunca entrou em combate")

    # ------------------------------------------------------------------
    # 4) ATTACK → FLEE: forçando o threshold só nesta instância (ADR 004:
    #    no balance atual flee_shield_threshold=0, FLEE por escudo desligado)
    # ------------------------------------------------------------------
    print("\n[4] ATTACK → FLEE (threshold forçado nesta instância)")
    npc_mgr.flee_shield_threshold = 40.0   # override local; não toca o balance global
    pirate.current_shields = 10.0          # abaixo do threshold forçado
    npc_mgr.update(dt)
    universe.update(dt)
    assert npc_mgr.npc_ships[pirate_id] == NPCBehavior.FLEE, npc_mgr.npc_ships[pirate_id]
    print("  ✓ com escudo baixo e threshold>0, o pirata foge")

    print("\nTeste de universo/IA: OK")


if __name__ == "__main__":
    main()
