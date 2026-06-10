"""
Teste headless do ExplorationManager (ADR 011) — SEM pygame.

Fase 1 (modelo + proximidade):
  1. POI oculto vira descoberto ao player entrar no raio; POI_DISCOVERED
     emitido UMA única vez.
  2. POI fora do raio continua oculto.
  3. Estações registradas entram já descobertas.
  4. Round-trip de save preserva o conjunto descoberto; IDs desconhecidos
     são ignorados; save antigo (sem campo) carrega com default.

Fase 3 (dados de localização como drop):
  5. reveal_random_hidden revela exatamente UM POI oculto; sem POI oculto,
     devolve None sem crash.
  6. LootManager gera "location_data" quando o rng cai abaixo da chance, e
     não gera quando cai acima.
  7. Cartografia via evento CARTOGRAPHY_PURCHASED revela N POIs.
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.event_bus import bus
from core.balance import balance
from entities.poi import PointOfInterest
from systems.exploration_manager import ExplorationManager
from systems.loot_manager import LootManager


class FakeStation:
    def __init__(self, sid, name, position):
        self.id = sid
        self.name = name
        self.position = list(position)


class FakeRng:
    """random() devolve valores enfileirados; choice pega o primeiro."""
    def __init__(self, values=None):
        self.values = list(values or [])

    def random(self):
        return self.values.pop(0) if self.values else 0.99

    def choice(self, seq):
        return seq[0]

    def randint(self, a, b):
        return a


def make_mgr(rng=None):
    bus._listeners.clear()
    mgr = ExplorationManager(rng=rng)
    mgr.register_station(FakeStation("station_alpha", "Hub Alpha", [400, 400]))
    mgr.register_poi(PointOfInterest(
        id="poi_near", name="Sinal Próximo", kind="signal",
        position=[1000.0, 0.0]))
    mgr.register_poi(PointOfInterest(
        id="poi_far", name="Sinal Distante", kind="signal",
        position=[99999.0, 99999.0]))
    return mgr


def main():
    print("=" * 60)
    print("Teste de Exploração (ADR 011)")
    print("=" * 60)

    assert "pygame" not in sys.modules, "exploration não deve importar pygame"
    radius = balance.exploration["discover_radius"]
    print(f"\n[0] Sem pygame; discover_radius={radius:.0f}  ✓")

    # ------------------------------------------------------------------
    # 1) Descoberta por proximidade, evento UMA vez
    # ------------------------------------------------------------------
    print("\n[1] POI descoberto ao entrar no raio; evento único")
    mgr = make_mgr()
    events = []
    bus.subscribe("POI_DISCOVERED", lambda d: events.append(d))

    # Longe de tudo: nada muda
    mgr.update(1 / 60, [50000.0, 50000.0])
    assert not mgr.pois["poi_near"].discovered
    assert events == []

    # Player entra no raio do poi_near (dist 0 < 700)
    mgr.update(1 / 60, [1000.0, 0.0])
    assert mgr.pois["poi_near"].discovered
    assert len(events) == 1 and events[0]["poi_id"] == "poi_near"
    assert events[0]["source"] == "proximity"

    # Updates seguintes NÃO reemitem
    for _ in range(10):
        mgr.update(1 / 60, [1000.0, 0.0])
    assert len(events) == 1, f"evento duplicado: {len(events)}"
    print("  ✓ descoberto no raio; POI_DISCOVERED emitido exatamente 1 vez")

    # ------------------------------------------------------------------
    # 2) POI fora do raio continua oculto
    # ------------------------------------------------------------------
    print("\n[2] POI distante continua oculto")
    assert not mgr.pois["poi_far"].discovered
    print("  ✓ poi_far segue oculto (fog-of-war)")

    # ------------------------------------------------------------------
    # 3) Estações já descobertas
    # ------------------------------------------------------------------
    print("\n[3] Estações registradas entram descobertas")
    st_poi = mgr.pois["poi_station_alpha"]
    assert st_poi.discovered and st_poi.kind == "station"
    assert mgr.hidden_count() == 1  # só poi_far
    print("  ✓ poi_station_alpha discovered=True; hidden_count=1")

    # ------------------------------------------------------------------
    # 4) Round-trip de save
    # ------------------------------------------------------------------
    print("\n[4] Save/load preserva o conjunto descoberto")
    saved = mgr.get_save_data()
    assert set(saved["discovered_ids"]) == {"poi_station_alpha", "poi_near"}

    mgr2 = make_mgr()  # mundo novo: poi_near oculto de novo
    assert not mgr2.pois["poi_near"].discovered
    mgr2.load_save_data(saved)
    assert mgr2.pois["poi_near"].discovered
    assert not mgr2.pois["poi_far"].discovered
    # ID desconhecido ignorado; save antigo (dict vazio) é no-op
    mgr2.load_save_data({"discovered_ids": ["poi_inexistente"]})
    mgr2.load_save_data({})
    mgr2.load_save_data(None)
    print("  ✓ round-trip OK; IDs desconhecidos e saves antigos tolerados")

    # ------------------------------------------------------------------
    # 5) reveal_random_hidden (drop de dados de localização)
    # ------------------------------------------------------------------
    print("\n[5] reveal_random_hidden revela exatamente um POI")
    mgr3 = make_mgr()
    hidden_before = mgr3.hidden_count()       # poi_near + poi_far = 2
    assert hidden_before == 2
    events3 = []
    bus.subscribe("POI_DISCOVERED", lambda d: events3.append(d))
    poi = mgr3.reveal_random_hidden()
    assert poi is not None and poi.discovered
    assert mgr3.hidden_count() == hidden_before - 1
    assert len(events3) == 1 and events3[0]["source"] == "location_data"

    # Esgota e confirma o no-op
    mgr3.reveal_random_hidden()
    assert mgr3.hidden_count() == 0
    assert mgr3.reveal_random_hidden() is None  # sem POI oculto → None
    print("  ✓ revela 1 por vez; sem ocultos → None sem crash")

    # ------------------------------------------------------------------
    # 6) LootManager: drop de location_data data-driven
    # ------------------------------------------------------------------
    print("\n[6] LootManager gera location_data pela chance configurada")
    chance = balance.exploration["location_drop_chance"]
    # rng baixo (< chance em ambas as rolagens: item_chance e location) → droppa
    lm_hit = LootManager(rng=FakeRng([0.0, 0.0]))
    loot = lm_hit.generate_loot("Small")
    assert "location_data" in loot["items"], loot
    # rng alto (acima da chance) → não droppa
    lm_miss = LootManager(rng=FakeRng([0.99, 0.99]))
    loot2 = lm_miss.generate_loot("Small")
    assert "location_data" not in loot2["items"], loot2
    print(f"  ✓ rng<{chance} droppa; rng alto não droppa")

    # ------------------------------------------------------------------
    # 7) Cartografia via evento revela N POIs
    # ------------------------------------------------------------------
    print("\n[7] CARTOGRAPHY_PURCHASED revela N POIs")
    mgr4 = make_mgr()
    assert mgr4.hidden_count() == 2
    bus.emit("CARTOGRAPHY_PURCHASED", {"count": 2})
    assert mgr4.hidden_count() == 0
    # Comprar de novo sem POIs ocultos: no-op sem crash
    bus.emit("CARTOGRAPHY_PURCHASED", {"count": 2})
    print("  ✓ revelou 2; repetir sem ocultos é no-op")

    print("\nTeste de exploração: OK")


if __name__ == "__main__":
    main()
