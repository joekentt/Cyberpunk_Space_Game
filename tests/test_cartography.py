"""
Teste da compra de cartografia na estação (Plano 06 Fase 4 / ADR 011).

Usa pygame com driver dummy (a StationUI cria fontes), mas sem janela real.

Valida:
  1. Com créditos suficientes: debita o preço, emite CARTOGRAPHY_PURCHASED e
     o ExplorationManager revela os POIs.
  2. Sem créditos: recusa com mensagem, NÃO debita, NÃO revela.
  3. Sem POIs ocultos: recusa com mensagem, NÃO debita.
  4. A opção CARTOGRAFIA aparece no menu principal da estação.
"""
import os
import sys

os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
os.environ.setdefault("SDL_AUDIODRIVER", "dummy")

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import pygame
pygame.init()
pygame.display.set_mode((960, 640))

from core.event_bus import bus
from core.balance import balance
from entities.ship import Ship
from entities.station import Station
from entities.poi import PointOfInterest
from systems.exploration_manager import ExplorationManager
from visual_engine.station_ui import StationUI


def make_world(credits):
    bus._listeners.clear()
    expl = ExplorationManager()
    station = Station(id="hub_a", name="Hub Alpha", position=[400, 400],
                      faction="United Humans",
                      services=["shipyard", "repair"])
    expl.register_station(station)
    for i in range(4):
        expl.register_poi(PointOfInterest(
            id=f"poi_{i}", name=f"Sinal {i}", kind="signal",
            position=[1000.0 * i, 2000.0]))
    player = Ship(id="player", name="Skiff", ship_class="Small",
                  model_id="starter_skiff", mass=120, energy_capacity=100,
                  heat_dissipation=8, max_hp=80, current_hp=80,
                  max_shields=100, current_shields=100,
                  is_player=True, faction="United Humans", credits=credits)
    base = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    ui = StationUI(960, 640, os.path.join(base, "data", "ships.json"))
    ui.open(station, player, hidden_poi_count=expl.hidden_count())
    return expl, station, player, ui


def main():
    print("=" * 60)
    print("Teste de Cartografia (Fase 4 / ADR 011)")
    print("=" * 60)

    price = balance.exploration["cartography_price"]
    count = balance.exploration["cartography_reveal_count"]
    print(f"\npreço={price}  reveal_count={count}")

    # ------------------------------------------------------------------
    # 1) Compra com créditos: debita, revela
    # ------------------------------------------------------------------
    print("\n[1] Compra com créditos suficientes")
    expl, station, player, ui = make_world(credits=10000)
    assert expl.hidden_count() == 4
    events = []
    bus.subscribe("POI_DISCOVERED", lambda d: events.append(d))

    ui._buy_cartography()
    assert player.credits == 10000 - price, player.credits
    assert expl.hidden_count() == 4 - count, expl.hidden_count()
    assert len(events) == count
    assert all(e["source"] == "cartography" for e in events)
    assert "Cartografia adquirida" in ui.message
    print(f"  ✓ debitou {price} cr; revelou {count} POIs; mensagem: '{ui.message}'")

    # ------------------------------------------------------------------
    # 2) Sem créditos: recusa, não debita, não revela
    # ------------------------------------------------------------------
    print("\n[2] Sem créditos: recusa sem efeitos")
    expl2, _, player2, ui2 = make_world(credits=100)
    hidden_before = expl2.hidden_count()
    ui2._buy_cartography()
    assert player2.credits == 100, "não deveria debitar"
    assert expl2.hidden_count() == hidden_before, "não deveria revelar"
    assert "insuficientes" in ui2.message
    print(f"  ✓ créditos intactos; nada revelado; mensagem: '{ui2.message}'")

    # ------------------------------------------------------------------
    # 3) Sem POIs ocultos: recusa, não debita
    # ------------------------------------------------------------------
    print("\n[3] Sem POIs ocultos: recusa sem debitar")
    expl3, _, player3, ui3 = make_world(credits=10000)
    ui3.hidden_poi_count = 0  # como se tudo já estivesse mapeado
    ui3._buy_cartography()
    assert player3.credits == 10000, "não deveria debitar sem dados à venda"
    assert "Sem novos dados" in ui3.message
    print(f"  ✓ sem débito; mensagem: '{ui3.message}'")

    # ------------------------------------------------------------------
    # 4) Opção no menu principal
    # ------------------------------------------------------------------
    print("\n[4] Opção CARTOGRAFIA no menu da estação")
    _, _, _, ui4 = make_world(credits=10000)
    keys = [k for _, k in ui4._main_options()]
    assert "cartography" in keys, keys
    label = next(lbl for lbl, k in ui4._main_options() if k == "cartography")
    assert "CARTOGRAFIA" in label
    print(f"  ✓ opção presente: '{label}'")

    print("\nTeste de cartografia: OK")


if __name__ == "__main__":
    main()
