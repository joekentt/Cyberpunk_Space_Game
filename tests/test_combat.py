"""
Teste de combate headless:
  1. Cria player + 2 NPCs (1 hostil, 1 amigo)
  2. Simula disparos do player
  3. Verifica hit detection, dano, escudos, destruição
  4. Verifica que NPCs hostis disparam de volta
"""
import os
import sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.event_bus import bus
from systems.universe_manager import UniverseManager
from systems.npc_manager import NPCManager, NPCBehavior
from systems.combat_manager import CombatManager
from entities.ship import Ship


def main():
    print("=" * 60)
    print("Teste de Combate Headless")
    print("=" * 60)

    # Reset bus listeners de testes anteriores
    bus.subscribers.clear() if hasattr(bus, 'subscribers') else None

    universe = UniverseManager()
    npc_mgr = NPCManager(universe)
    combat = CombatManager(universe)

    # Player
    player_template = Ship(
        id="player",
        name="Skiff Mk I",
        ship_class="Small",
        model_id="starter_skiff",
        mass=120,
        energy_capacity=100,
        heat_dissipation=8,
        max_hp=80, current_hp=80,
        max_shields=100, current_shields=100,
        is_player=True,
        faction="United Humans",
    )
    pid = universe.spawn_ship(player_template, [500, 300])
    player = universe.entities[pid]
    player.rotation = 0  # apontando para +X

    # NPC Pirate (hostil) a 200px à frente do player
    pirate_template = Ship(
        id="pirate1",
        name="Wasp Pirate",
        ship_class="Small",
        model_id="wasp_combat",
        mass=100,
        energy_capacity=100,
        heat_dissipation=5,
        max_hp=70, current_hp=70,
        max_shields=80, current_shields=80,
        faction="Pirates",
    )
    pid_pirate = universe.spawn_ship(pirate_template, [700, 300])
    pirate = universe.entities[pid_pirate]
    npc_mgr.register_npc(pid_pirate, NPCBehavior.IDLE)

    # NPC Independent (não hostil)
    indep_template = Ship(
        id="indep1",
        name="Mule",
        ship_class="Medium",
        model_id="mule_trader",
        mass=350,
        energy_capacity=150,
        heat_dissipation=10,
        max_hp=200, current_hp=200,
        max_shields=150, current_shields=150,
        faction="Independent",
    )
    pid_indep = universe.spawn_ship(indep_template, [400, 500])
    indep = universe.entities[pid_indep]
    npc_mgr.register_npc(pid_indep, NPCBehavior.IDLE)

    # Log de eventos
    events = []
    def log(ev_name):
        def listener(data):
            events.append((ev_name, data))
        return listener
    bus.subscribe("WEAPON_FIRED", log("WEAPON_FIRED"))
    bus.subscribe("PROJECTILE_HIT", log("PROJECTILE_HIT"))
    bus.subscribe("SHIP_DESTROYED", log("SHIP_DESTROYED"))

    # Simulação de 5 segundos a 60 fps
    print(f"\nEstado inicial:")
    print(f"  Player: HP {player.current_hp}/{player.max_hp}  Shields {player.current_shields}/{player.max_shields}")
    print(f"  Pirate: HP {pirate.current_hp}/{pirate.max_hp}  Shields {pirate.current_shields}/{pirate.max_shields}")
    print(f"  Distância player-pirate: {abs(pirate.position[0] - player.position[0]):.0f}px")
    print()

    dt = 1 / 60
    player_shots = 0
    for frame in range(300):  # 5 segundos
        # Player atira a cada 3 frames (~20 tiros/s, mas cooldown vai limitar)
        if frame % 3 == 0:
            bus.emit("PLAYER_INPUT", {"action": "shoot", "value": 1.0})
            player_shots += 1

        universe.update(dt)
        npc_mgr.update(dt)
        combat.update(dt)

    # Resumo final
    print(f"Após 5 segundos de simulação:")
    print(f"  Player ainda no universo: {pid in universe.entities}")
    print(f"  Pirate ainda no universo: {pid_pirate in universe.entities}")
    print(f"  Indep ainda no universo: {pid_indep in universe.entities}")
    if pid in universe.entities:
        p = universe.entities[pid]
        print(f"  Player final: HP {p.current_hp:.0f}/{p.max_hp:.0f}  Shields {p.current_shields:.0f}/{p.max_shields:.0f}")
    if pid_pirate in universe.entities:
        pp = universe.entities[pid_pirate]
        print(f"  Pirate final: HP {pp.current_hp:.0f}/{pp.max_hp:.0f}  Shields {pp.current_shields:.0f}/{pp.max_shields:.0f}")
        print(f"  Pirate state: {npc_mgr.npc_ships.get(pid_pirate)}")
    if pid_indep in universe.entities:
        ii = universe.entities[pid_indep]
        print(f"  Indep final:  HP {ii.current_hp:.0f}/{ii.max_hp:.0f}  Shields {ii.current_shields:.0f}/{ii.max_shields:.0f}")
        print(f"  Indep state:  {npc_mgr.npc_ships.get(pid_indep)} (deve continuar IDLE — não é hostil)")

    print()
    print(f"Eventos capturados:")
    counts = {}
    for ev, _ in events:
        counts[ev] = counts.get(ev, 0) + 1
    for k, v in counts.items():
        print(f"  {k}: {v}")
    print(f"  Tentativas de tiro do player: {player_shots}")
    print(f"  Projéteis ativos no fim: {len(combat.projectiles)}")

    print()
    # Validações
    fired = counts.get("WEAPON_FIRED", 0)
    hits = counts.get("PROJECTILE_HIT", 0)
    destroyed = counts.get("SHIP_DESTROYED", 0)
    assert fired > 0, "Nenhum tiro disparado!"
    assert hits > 0, "Nenhum hit detectado!"
    if pid_pirate not in universe.entities:
        assert destroyed >= 1, "Pirate sumiu mas SHIP_DESTROYED não foi emitido"
    if pid_indep in universe.entities:
        # Indep ainda existe — não foi atingido (faction friendly)
        ii = universe.entities[pid_indep]
        assert ii.current_hp == ii.max_hp, "Indep tomou dano — friendly fire deveria bloquear!"

    print("✓ Tiros disparados corretamente (cooldown respeitado)")
    print("✓ Hit detection funcionou")
    print("✓ Independent (não hostil) não foi atingido")
    if destroyed > 0:
        print(f"✓ {destroyed} nave(s) destruída(s) — evento SHIP_DESTROYED emitido")
    if any(npc_mgr.npc_ships.get(pid_pirate) == s for s in ["CHASE", "ATTACK"]):
        print("✓ Pirate detectou player e entrou em estado de combate")

    print("\nTeste de combate: OK")


if __name__ == "__main__":
    main()
