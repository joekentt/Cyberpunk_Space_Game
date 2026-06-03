"""
Teste de balanceamento de combate (headless, sem pygame) — Ciclo B.

Valida, por simulação com a IA e o combate REAIS, que o duelo inicial é justo:

  1. Duelo 1v1 (Skiff do player vs 1 pirata na Wasp): é DISPUTADO — não acaba
     instantaneamente (>= X s) nem é eterno (<= Y s), e o player vence com
     esforço na maioria das amostras.
  2. Comprar a Wasp melhora PERCEPTIVELMENTE a ofensiva (mata o pirata bem
     mais rápido que na Skiff).
  3. 2 piratas vs Skiff: a Skiff sobrevive tempo suficiente para reagir
     (> Z s antes de poder ser destruída).
  4. A fórmula de firepower nova bate com os valores esperados do catálogo.

Combate tem aleatoriedade (chance de disparo da IA) — rodamos várias amostras
com seeds fixas e validamos FAIXAS/medianas, não igualdades exatas.

Faixas escolhidas (e por quê):
  X = 2.0 s  — piso de "não instantâneo". Com mira perfeita o player leva
               ~3 s para vencer o pirata (150 de HP efetivo / ~48 dps), então
               2 s é um piso seguro que ainda pega regressões de "delete".
  Y = 25.0 s — teto de "não eterno". Um duelo saudável resolve em < ~8 s;
               25 s deixa margem para azar de RNG sem mascarar travas reais.
  Z = 3.0 s  — a Skiff precisa de pelo menos 3 s sob fogo de 2 Wasps antes de
               poder ser destruída, dando ao jogador tempo de reagir/fugir.
"""
import os
import sys
import math
import random
import statistics

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import json
from core.event_bus import bus
from core.balance import balance
from systems.universe_manager import UniverseManager
from systems.npc_manager import NPCManager, NPCBehavior
from systems.combat_manager import CombatManager
from systems.energy_manager import EnergyManager
from entities.ship import Ship

X_MIN_DUEL = 2.0     # s — duelo não pode acabar antes disto
Y_MAX_DUEL = 25.0    # s — duelo precisa resolver antes disto
Z_MIN_SURVIVE = 3.0  # s — Skiff deve sobreviver a 2 Wasps por mais que isto

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def load_catalog():
    with open(os.path.join(ROOT, "data", "ships.json"), encoding="utf-8") as f:
        return {s["id"]: s for s in json.load(f)["ships"]}


CATALOG = load_catalog()


def make_template(ship_id, is_player=False, faction=None):
    t = Ship.from_dict(CATALOG[ship_id])
    t.is_player = is_player
    if faction:
        t.faction = faction
    return t


def _angle_to(a, b):
    return math.degrees(math.atan2(b[1] - a[1], b[0] - a[0]))


def run_scenario(player_ship_id, enemies, seed, *, player_fires=True,
                 max_time=30.0):
    """
    Simula um cenário de combate. `enemies` é uma lista de (ship_id, position).
    O player fica no centro, mira no inimigo vivo mais próximo e dispara com
    cadência realista (cooldown do CombatManager limita). Retorna métricas.
    """
    random.seed(seed)
    bus._listeners.clear()

    universe = UniverseManager()
    npc = NPCManager(universe)
    combat = CombatManager(universe)

    # Player no centro
    player_tpl = make_template(player_ship_id, is_player=True,
                               faction="United Humans")
    pid = universe.spawn_ship(player_tpl, [0.0, 0.0])
    player = universe.entities[pid]
    energy = EnergyManager(player)

    # Inimigos (piratas na Wasp por padrão). Já nascem VOLTADOS para o player
    # (engajados) — representa um pirata que te ameaça, não uma emboscada pelas
    # costas; spawn_ship zera a rotação, então ajustamos após o spawn.
    enemy_ids = []
    for ship_id, pos in enemies:
        tpl = make_template(ship_id, faction="Pirates")
        eid = universe.spawn_ship(tpl, list(pos))
        universe.entities[eid].rotation = _angle_to(pos, player.position)
        npc.register_npc(eid, NPCBehavior.IDLE)
        enemy_ids.append(eid)

    destroyed_at = {}

    def on_destroyed(data):
        sid = data["ship_id"]
        destroyed_at.setdefault(sid, t)

    bus.subscribe("SHIP_DESTROYED", on_destroyed)

    dt = 1 / 60
    t = 0.0
    steps = int(max_time / dt)
    for _ in range(steps):
        # Mira no inimigo vivo mais próximo
        alive = [universe.entities[e] for e in enemy_ids if e in universe.entities]
        if alive and pid in universe.entities:
            nearest = min(alive, key=lambda s: (s.position[0] - player.position[0]) ** 2
                          + (s.position[1] - player.position[1]) ** 2)
            player.rotation = _angle_to(player.position, nearest.position)
            if player_fires:
                bus.emit("PLAYER_INPUT", {"action": "shoot", "value": 1.0})

        universe.update(dt)
        npc.update(dt)
        combat.update(dt)
        if pid in universe.entities:
            energy.update(dt)

        t += dt

        player_dead = pid not in universe.entities
        enemies_dead = all(e not in universe.entities for e in enemy_ids)
        if player_dead or enemies_dead:
            break

    player_alive = pid in universe.entities
    return {
        "duration": t,
        "player_alive": player_alive,
        "player_hp": player.current_hp if player_alive else 0.0,
        "player_shields": player.current_shields if player_alive else 0.0,
        "player_destroyed_at": destroyed_at.get(pid),
        "enemy_destroyed_times": [destroyed_at[e] for e in enemy_ids if e in destroyed_at],
        "enemies_alive": [e for e in enemy_ids if e in universe.entities],
    }


def main():
    print("=" * 60)
    print("Teste de Balanceamento de Combate")
    print("=" * 60)

    # ------------------------------------------------------------------
    # 4) Fórmula de firepower bate com o catálogo (curva achatada)
    # ------------------------------------------------------------------
    print("\n[4] Firepower derivado do catálogo (curva achatada)")
    exp_fp = {
        "starter_skiff": 2 ** 0.6,
        "wasp_combat": 6 ** 0.6,
        "mule_trader": 3 ** 0.6,
        "albatross_explorer": 1.0,
        "stingray_raider": 5 ** 0.6,
    }
    for sid, exp in exp_fp.items():
        got = CombatManager.hardpoint_firepower(Ship.from_dict(CATALOG[sid]))
        assert abs(got - exp) < 1e-9, f"{sid}: {got} != {exp}"
        print(f"  {CATALOG[sid]['name']:16s} x{got:.2f}")
    ratio = exp_fp["wasp_combat"] / exp_fp["starter_skiff"]
    assert 1.8 <= ratio <= 2.5, f"razão Wasp/Skiff {ratio:.2f} fora de 1.8–2.5"
    print(f"  Razão ofensiva Wasp/Skiff: {ratio:.2f}x  ✓")

    # ------------------------------------------------------------------
    # 1) Duelo 1v1: Skiff vs 1 pirata Wasp — disputado e vencível
    # ------------------------------------------------------------------
    print("\n[1] Duelo 1v1 — Skiff (player) vs Wasp (pirata) @ 320px")
    seeds = [1, 2, 3, 4, 5, 6, 7, 8]
    durations = []
    end_defense = []   # HP+escudo restantes do player ao vencer (mede o "esforço")
    wins = 0
    for s in seeds:
        r = run_scenario("starter_skiff", [("wasp_combat", [320, 0])], seed=s)
        durations.append(r["duration"])
        won = r["player_alive"] and not r["enemies_alive"]
        wins += 1 if won else 0
        if won:
            end_defense.append(r["player_hp"] + r["player_shields"])
    med = statistics.median(durations)
    # Defesa inicial da Skiff = 80 HP + 100 escudo = 180. Quanto sobra mede esforço.
    mean_left = statistics.mean(end_defense)
    print(f"  durações: {[f'{d:.1f}' for d in durations]}")
    print(f"  mediana {med:.1f}s | min {min(durations):.1f}s | max {max(durations):.1f}s")
    print(f"  vitórias do player: {wins}/{len(seeds)}")
    print(f"  defesa média restante: {mean_left:.0f}/180 (HP+escudo)")
    assert min(durations) >= X_MIN_DUEL, \
        f"duelo rápido demais ({min(durations):.1f}s < {X_MIN_DUEL}s)"
    assert max(durations) <= Y_MAX_DUEL, \
        f"duelo longo demais ({max(durations):.1f}s > {Y_MAX_DUEL}s)"
    assert wins >= len(seeds) - 1, \
        f"player deveria vencer na maioria ({wins}/{len(seeds)})"
    # "Com esforço": o player não pode sair ileso — em média perde defesa real
    # (pelo menos ~40 de 180). Pega regressões que tornem o pirata inofensivo.
    assert mean_left <= 140.0, \
        f"pirata inofensivo demais — player mal tomou dano (sobrou {mean_left:.0f}/180)"
    print("  ✓ duelo disputado, vencível e com custo real (esforço)")

    # ------------------------------------------------------------------
    # 2) Comprar a Wasp melhora perceptivelmente a ofensiva
    # ------------------------------------------------------------------
    print("\n[2] Upgrade Skiff → Wasp encurta o tempo de abate do pirata")
    def median_kill_time(player_id):
        kills = []
        for s in seeds:
            r = run_scenario(player_id, [("wasp_combat", [320, 0])], seed=s)
            if r["enemy_destroyed_times"]:
                kills.append(r["enemy_destroyed_times"][0])
        return statistics.median(kills) if kills else None

    skiff_kt = median_kill_time("starter_skiff")
    wasp_kt = median_kill_time("wasp_combat")
    print(f"  tempo p/ matar o pirata — Skiff: {skiff_kt:.1f}s | Wasp: {wasp_kt:.1f}s")
    assert wasp_kt is not None and skiff_kt is not None
    assert wasp_kt < skiff_kt * 0.75, \
        f"Wasp deveria matar bem mais rápido (Wasp {wasp_kt:.1f}s vs Skiff {skiff_kt:.1f}s)"
    print(f"  ✓ Wasp mata ~{skiff_kt / wasp_kt:.1f}x mais rápido — upgrade perceptível")

    # ------------------------------------------------------------------
    # 3) 2 piratas vs Skiff — sobrevive tempo para reagir
    # ------------------------------------------------------------------
    print("\n[3] 2 Wasps piratas vs Skiff — tempo de sobrevivência")
    survive_times = []
    for s in seeds:
        # Player NÃO atira: medimos o pior caso (puro fogo recebido).
        r = run_scenario("starter_skiff",
                         [("wasp_combat", [330, -40]), ("wasp_combat", [330, 40])],
                         seed=s, player_fires=False, max_time=20.0)
        # tempo até o player poder ser destruído (ou sobreviveu o teste todo)
        t_death = r["player_destroyed_at"] if r["player_destroyed_at"] else r["duration"]
        survive_times.append(t_death)
    print(f"  tempos até morte: {[f'{d:.1f}' for d in survive_times]}")
    print(f"  min {min(survive_times):.1f}s | mediana {statistics.median(survive_times):.1f}s")
    assert min(survive_times) > Z_MIN_SURVIVE, \
        f"Skiff morre rápido demais p/ 2 Wasps ({min(survive_times):.1f}s <= {Z_MIN_SURVIVE}s)"
    print(f"  ✓ Skiff sobrevive > {Z_MIN_SURVIVE}s sob fogo de 2 Wasps (tempo de reagir)")

    print("\nTeste de balanceamento: OK")


if __name__ == "__main__":
    main()
