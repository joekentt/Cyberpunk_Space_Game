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

from core.balance import balance
from systems.universe_manager import UniverseManager
from systems.combat_manager import CombatManager, DEFAULT_WEAPONS
from entities.ship import Ship


def load_catalog():
    path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                        "data", "ships.json")
    with open(path, encoding="utf-8") as f:
        return {s["id"]: s for s in json.load(f)["ships"]}


def expected_firepower(hp):
    """Réplica independente da fórmula (curva achatada, data-driven)."""
    fp = balance.firepower
    raw = (hp.get("weapon_small", 0) * fp["weight_small"]
           + hp.get("weapon_medium", 0) * fp["weight_medium"]
           + hp.get("weapon_large", 0) * fp["weight_large"])
    return float(fp["fallback"]) if raw <= 0 else float(raw) ** float(fp["exponent"])


def main():
    print("=" * 60)
    print("Teste de Hardpoints (poder de fogo)")
    print("=" * 60)

    catalog = load_catalog()

    # ------------------------------------------------------------------
    # 1) firepower derivado corretamente do ships.json (curva ACHATADA)
    # ------------------------------------------------------------------
    print("\n[1] firepower derivado do ships.json")
    # Valores da curva data-driven (pesos 1/2/4, expoente 0.6).
    expected = {
        "starter_skiff": 2 ** 0.6,         # 2S  → ~1.52
        "wasp_combat": 6 ** 0.6,           # 4S+1M (raw 6) → ~2.93
        "albatross_explorer": 1.0,         # 1S  → 1.0
        "mule_trader": 3 ** 0.6,           # 1S+1M (raw 3) → ~1.93
        "stingray_raider": 5 ** 0.6,       # 3S+1M (raw 5) → ~2.63
        "terraformador_ligeiro": 1.0,      # 1S  → 1.0
    }
    for ship_id, exp in expected.items():
        ship = Ship.from_dict(catalog[ship_id])
        got = CombatManager.hardpoint_firepower(ship)
        raw = expected_firepower(catalog[ship_id]["hardpoints"])
        assert abs(got - exp) < 1e-9, f"{ship_id}: firepower {got} (esperado {exp})"
        assert abs(got - raw) < 1e-9, f"{ship_id}: divergiu da fórmula crua ({raw})"
        print(f"  {catalog[ship_id]['name']:16s} → x{got:.2f}  ✓")

    # Curva achatada: a melhor nave de combate Tier 1 (Wasp) deve ter entre
    # 1.8x e 2.5x a capacidade ofensiva da Skiff (não mais 3.5x).
    ratio = expected["wasp_combat"] / expected["starter_skiff"]
    print(f"\n  Razão Wasp/Skiff = {ratio:.2f}x (alvo 1.8–2.5)")
    assert 1.8 <= ratio <= 2.5, f"razão Wasp/Skiff fora do alvo: {ratio:.2f}"

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
    print(f"  Skiff: {skiff_dmg:.1f} de dano/tiro (base {base:g} x{expected['starter_skiff']:.2f})")
    print(f"  Wasp:  {wasp_dmg:.1f} de dano/tiro (base {base:g} x{expected['wasp_combat']:.2f})")
    assert abs(skiff_dmg - base * expected["starter_skiff"]) < 1e-6
    assert abs(wasp_dmg - base * expected["wasp_combat"]) < 1e-6
    assert wasp_dmg > skiff_dmg, "Wasp deveria causar mais dano que a Skiff"
    print(f"  Wasp ({wasp_dmg:.1f}) > Skiff ({skiff_dmg:.1f})  ✓")

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
