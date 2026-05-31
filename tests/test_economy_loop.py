"""
Teste headless do loop de economia por abate.

Valida:
  - attacker_id propaga de _apply_hit → _destroy_ship → evento SHIP_DESTROYED
  - player destrói inimigo → player.credits aumenta dentro da faixa da ship_class
  - NPC destrói NPC → player.credits NÃO muda
  - faixas por classe: Small 50-150, Medium 200-500, Large 1000-2500
"""
import os
import sys
import math

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.event_bus import bus
from systems.universe_manager import UniverseManager
from systems.combat_manager import CombatManager
from systems.loot_manager import LootManager
from entities.ship import Ship
from entities.projectile import Projectile


# ---- helpers -----------------------------------------------------------------

def make_ship(uid, ship_class="Small", faction="Pirates", is_player=False,
              credits=0, hp=10.0, shields=0.0, pos=None):
    s = Ship(
        id=uid, name=uid, ship_class=ship_class,
        model_id=uid, mass=120,
        energy_capacity=100, heat_dissipation=5,
        max_hp=hp, current_hp=hp,
        max_shields=shields, current_shields=shields,
        is_player=is_player, faction=faction, credits=credits,
    )
    if pos:
        s.position = list(pos)
    return s


def fatal_projectile(owner_id, owner_faction, target):
    """Cria um projétil que inflige 9999 de dano (mata qualquer nave)."""
    rad = math.radians(0)
    return Projectile(
        id=f"proj_{owner_id}",
        owner_id=owner_id,
        faction=owner_faction,
        position=list(target.position),
        velocity=[0.0, 0.0],
        damage=9999.0,
        weapon_type="kinetic",
        color=(255, 200, 80),
        lifetime=10.0,
        radius=50.0,   # raio enorme garante hit
    )


def reward_handler(player_id, player_ship, loot_mgr, received):
    """Retorna um callback de SHIP_DESTROYED que credita o player como main_pygame faz."""
    def _handler(data):
        if data.get("ship_id") == player_id:
            return          # player morreu — sem recompensa
        if data.get("attacker_id") != player_id:
            return          # NPC matou NPC — sem recompensa
        loot = loot_mgr.generate_loot(data.get("ship_class", "Small"))
        player_ship.credits += loot["credits"]
        received.append(loot["credits"])
    return _handler


# ---- testes ------------------------------------------------------------------

def main():
    print("=" * 60)
    print("Teste de Economy Loop (recompensa por abate)")
    print("=" * 60)

    loot_mgr = LootManager()
    RANGES = {
        "Small":  (50, 150),
        "Medium": (200, 500),
        "Large":  (1000, 2500),
    }

    # ------------------------------------------------------------------
    # 1) attacker_id propaga pela cadeia combat: _apply_hit → SHIP_DESTROYED
    # ------------------------------------------------------------------
    print("\n[1] attacker_id propaga na cadeia CombatManager")
    universe1 = UniverseManager()
    combat1 = CombatManager(universe1)

    player1 = make_ship("player1", faction="United Humans", is_player=True, hp=100)
    enemy1 = make_ship("npc_small", faction="Pirates", ship_class="Small", hp=10.0)
    universe1.entities["player1"] = player1
    universe1.entities["npc_small"] = enemy1

    destroyed_events = []
    def _on_destroyed(data):
        destroyed_events.append(data)
    bus.subscribe("SHIP_DESTROYED", _on_destroyed)

    proj = fatal_projectile("player1", "United Humans", enemy1)
    combat1._apply_hit(proj, enemy1)

    bus.unsubscribe("SHIP_DESTROYED", _on_destroyed)

    assert len(destroyed_events) == 1, "deveria emitir SHIP_DESTROYED"
    ev = destroyed_events[0]
    assert ev["ship_id"] == "npc_small"
    assert ev["attacker_id"] == "player1", \
        f"attacker_id deveria ser 'player1', foi '{ev.get('attacker_id')}'"
    assert ev["ship_class"] == "Small"
    print(f"  SHIP_DESTROYED emitido com attacker_id='{ev['attacker_id']}'  ✓")

    # ------------------------------------------------------------------
    # 2) Player destrói inimigo → créditos aumentam dentro da faixa Small
    # ------------------------------------------------------------------
    print("\n[2] Player destrói Small → créditos aumentam na faixa correta")
    universe2 = UniverseManager()
    combat2 = CombatManager(universe2)

    player2 = make_ship("player2", faction="United Humans", is_player=True, credits=1000)
    enemy_s = make_ship("npc_s", faction="Pirates", ship_class="Small", hp=10.0)
    universe2.entities["player2"] = player2
    universe2.entities["npc_s"] = enemy_s

    received_s = []
    handler_s = reward_handler("player2", player2, loot_mgr, received_s)
    bus.subscribe("SHIP_DESTROYED", handler_s)

    proj_s = fatal_projectile("player2", "United Humans", enemy_s)
    combat2._apply_hit(proj_s, enemy_s)

    bus.unsubscribe("SHIP_DESTROYED", handler_s)

    assert len(received_s) == 1, "deveria ter recebido 1 recompensa"
    reward = received_s[0]
    lo, hi = RANGES["Small"]
    assert lo <= reward <= hi, f"Small: recompensa {reward} fora da faixa [{lo}, {hi}]"
    assert player2.credits == 1000 + reward
    print(f"  recompensa Small: +{reward} cr (faixa [{lo}–{hi}])  ✓")
    print(f"  créditos: 1000 → {player2.credits}  ✓")

    # ------------------------------------------------------------------
    # 3) NPC destrói NPC → créditos do player NÃO mudam
    # ------------------------------------------------------------------
    print("\n[3] NPC destrói NPC → créditos do player inalterados")
    universe3 = UniverseManager()
    combat3 = CombatManager(universe3)

    player3 = make_ship("player3", faction="United Humans", is_player=True, credits=500)
    enemy_a = make_ship("npc_a", faction="Pirates", ship_class="Medium", hp=10.0)
    enemy_b = make_ship("npc_b", faction="Independent", ship_class="Small", hp=10.0)
    universe3.entities["player3"] = player3
    universe3.entities["npc_a"] = enemy_a
    universe3.entities["npc_b"] = enemy_b

    received_npc = []
    handler_npc = reward_handler("player3", player3, loot_mgr, received_npc)
    bus.subscribe("SHIP_DESTROYED", handler_npc)

    # NPC "npc_a" (pirata) mata NPC "npc_b" (independente)
    proj_npc = fatal_projectile("npc_a", "Pirates", enemy_b)
    combat3._apply_hit(proj_npc, enemy_b)

    bus.unsubscribe("SHIP_DESTROYED", handler_npc)

    assert received_npc == [], "player NÃO deveria receber nada quando NPC mata NPC"
    assert player3.credits == 500, f"créditos não devem mudar, foi {player3.credits}"
    print("  nenhuma recompensa gerada  ✓")
    print("  créditos do player inalterados (500)  ✓")

    # ------------------------------------------------------------------
    # 4) Faixas por classe (Medium e Large)
    # ------------------------------------------------------------------
    print("\n[4] Faixas de recompensa por ship_class")
    for ship_class in ("Medium", "Large"):
        lo, hi = RANGES[ship_class]
        # Amostra 10 vezes para cobrir aleatoriedade
        for _ in range(10):
            loot = loot_mgr.generate_loot(ship_class)
            c = loot["credits"]
            assert lo <= c <= hi, \
                f"{ship_class}: {c} fora da faixa [{lo}, {hi}]"
        print(f"  {ship_class}: faixa [{lo}–{hi}] respeitada (10 amostras)  ✓")

    print("\nTeste de economy loop: OK")


if __name__ == "__main__":
    main()
