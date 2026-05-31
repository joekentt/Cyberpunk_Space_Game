"""
Teste headless do poder de fogo derivado de hardpoints.

Valida:
  - firepower é derivado corretamente do ships.json (fórmula ponderada)
  - uma nave com mais hardpoints de arma causa mais dano por salva que a Skiff
  - o dano por disparo no CombatManager.fire escala com os hardpoints
  - naves sem hardpoint de arma têm fallback (1.0) e não crasham
"""
import os
import sys
import json

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from systems.universe_manager import UniverseManager
from systems.combat_manager import CombatManager, DEFAULT_WEAPONS
from entities.ship import Ship


def load_catalog():
    path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                        "data", "ships.json")
    with open(path, encoding="utf-8") as f:
        return {s["id"]: s for s in json.load(f)["ships"]}


def expected_firepower(hp):
    fp = (hp.get("weapon_small", 0) * 1
          + hp.get("weapon_medium", 0) * 3
          + hp.get("weapon_large", 0) * 9)
    return float(fp) if fp > 0 else 1.0


def main():
    print("=" * 60)
    print("Teste de Hardpoints (poder de fogo)")
    print("=" * 60)

    catalog = load_catalog()

    # ------------------------------------------------------------------
    # 1) firepower derivado corretamente do ships.json
    # ------------------------------------------------------------------
    print("\n[1] firepower derivado do ships.json")
    expected = {
        "starter_skiff": 2.0,       # 2S
        "wasp_combat": 7.0,         # 4S + 1M
        "albatross_explorer": 1.0,  # 1S
        "mule_trader": 4.0,         # 1S + 1M
    }
    for ship_id, exp in expected.items():
        ship = Ship.from_dict(catalog[ship_id])
        got = CombatManager.hardpoint_firepower(ship)
        # confere também contra a fórmula aplicada aos dados crus
        raw = expected_firepower(catalog[ship_id]["hardpoints"])
        assert got == exp == raw, \
            f"{ship_id}: firepower {got} (esperado {exp}, fórmula {raw})"
        print(f"  {catalog[ship_id]['name']:12s} → x{got:g}  ✓")

    # ------------------------------------------------------------------
    # 2) Wasp causa mais dano por salva que a Skiff
    # ------------------------------------------------------------------
    print("\n[2] Wasp causa mais dano por salva que a Skiff")
    universe = UniverseManager()
    combat = CombatManager(universe)
    base = DEFAULT_WEAPONS["kinetic_small"]["damage"]

    def salvo_damage(ship_id):
        ship = Ship.from_dict(catalog[ship_id])
        ship.id = ship_id  # id único para a chave de cooldown
        ship.rotation = 0.0
        ok = combat.fire(ship, weapon_id="kinetic_small")
        assert ok, f"{ship_id} não conseguiu disparar"
        # o último projétil criado é o desta nave
        proj = combat.projectiles[f"proj_{combat._next_id - 1}"]
        return proj.damage

    skiff_dmg = salvo_damage("starter_skiff")
    wasp_dmg = salvo_damage("wasp_combat")
    print(f"  Skiff: {skiff_dmg:g} de dano/tiro (base {base:g} x2)")
    print(f"  Wasp:  {wasp_dmg:g} de dano/tiro (base {base:g} x7)")
    assert skiff_dmg == base * 2.0, f"Skiff deveria ser {base*2}, foi {skiff_dmg}"
    assert wasp_dmg == base * 7.0, f"Wasp deveria ser {base*7}, foi {wasp_dmg}"
    assert wasp_dmg > skiff_dmg, "Wasp deveria causar mais dano que a Skiff"
    print(f"  Wasp ({wasp_dmg:g}) > Skiff ({skiff_dmg:g})  ✓")

    # ------------------------------------------------------------------
    # 3) Fallback: nave sem hardpoint de arma não crasha e usa x1
    # ------------------------------------------------------------------
    print("\n[3] Fallback para nave sem hardpoint de arma")
    unarmed = Ship(
        id="unarmed", name="Drone Civil", ship_class="Small",
        model_id="drone", mass=80, energy_capacity=50, heat_dissipation=5,
        max_hp=40, current_hp=40, max_shields=0, current_shields=0,
        faction="Independent",
        hardpoints={"weapon_small": 0, "weapon_medium": 0,
                    "weapon_large": 0, "utility": 2},
    )
    fp = CombatManager.hardpoint_firepower(unarmed)
    assert fp == 1.0, f"fallback deveria ser 1.0, foi {fp}"
    ok = combat.fire(unarmed, weapon_id="kinetic_small")
    assert ok, "disparo da nave sem arma falhou"
    proj = combat.projectiles[f"proj_{combat._next_id - 1}"]
    assert proj.damage == base * 1.0, f"dano deveria ser {base}, foi {proj.damage}"
    print(f"  nave sem arma → x{fp:g} (dano {proj.damage:g}), sem crash  ✓")

    # Nave totalmente sem o campo hardpoints (dict vazio) também não crasha
    no_field = Ship(
        id="nofield", name="Sucata", ship_class="Small", model_id="x",
        mass=80, energy_capacity=50, heat_dissipation=5,
        max_hp=40, current_hp=40, max_shields=0, current_shields=0,
    )
    assert CombatManager.hardpoint_firepower(no_field) == 1.0
    print("  nave com hardpoints vazio → x1, sem crash  ✓")

    print("\nTeste de hardpoints: OK")


if __name__ == "__main__":
    main()
