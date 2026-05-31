"""
Teste headless do loop de missões (BOUNTY).

Valida:
  - Templates BOUNTY têm objetivo KILL com target_faction
  - Ciclo completo: gerar → aceitar → matar N vezes → completar → ADD_CREDITS emitido
  - Kills intermediários não completam a missão antes do contador
  - Kills de facção errada não contam
  - Múltiplas missões rastreadas independentemente
"""
import os
import sys
import json

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from systems.mission_manager import MissionManager
from entities.mission import MissionStatus
from core.event_bus import bus


def load_bounty_templates():
    path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                        "data", "mission_templates.json")
    with open(path, encoding="utf-8") as f:
        all_templates = json.load(f)["templates"]
    return [t for t in all_templates if t["type"] == "BOUNTY"]


def main():
    print("=" * 60)
    print("Teste do Mission Loop")
    print("=" * 60)

    bounty_templates = load_bounty_templates()
    assert bounty_templates, "Nenhum template BOUNTY encontrado"

    # ------------------------------------------------------------------
    # 1) Templates têm objetivo KILL com target_faction
    # ------------------------------------------------------------------
    print("\n[1] Templates BOUNTY têm objetivo KILL com target_faction")
    for t in bounty_templates:
        kill_obj = next((o for o in t["objectives"] if o.get("type") == "KILL"), None)
        assert kill_obj is not None, f"Template BOUNTY sem objetivo KILL: {t['title']}"
        assert "target_faction" in kill_obj, \
            f"Objetivo KILL sem target_faction: {t['title']}"
        assert kill_obj.get("count", 0) > 0, \
            f"Objetivo KILL com count=0: {t['title']}"
    print(f"  {len(bounty_templates)} template(s) OK  ✓")

    # ------------------------------------------------------------------
    # 2) Ciclo completo: gerar → aceitar → kills → completar
    # ------------------------------------------------------------------
    print("\n[2] Ciclo completo: gerar → aceitar → kills → completar")
    mgr = MissionManager()
    mgr.set_templates(bounty_templates)

    credits_received = []
    bus.subscribe("ADD_CREDITS", credits_received.append)
    try:
        mission = mgr.generate_mission(faction="United Humans", difficulty=1.0)
        assert mission.id in mgr.available_missions
        print(f"  Missão gerada: '{mission.title}' +{mission.reward_credits} cr")

        mgr.accept_mission(mission.id)
        assert mission.id in mgr.active_missions
        assert mission.id not in mgr.available_missions
        assert mission.status == MissionStatus.ACTIVE
        print("  Missão aceita  ✓")

        kill_obj = next(o for o in mission.objectives if o.get("type") == "KILL")
        target_faction = kill_obj["target_faction"]
        required = kill_obj["count"]

        # Kills intermediários: não deve completar ainda
        for i in range(required - 1):
            mgr.record_kill(target_faction)
        assert mission.kill_progress == required - 1
        assert mission.id in mgr.active_missions, "Missão completou cedo demais"
        print(f"  {required - 1}/{required} kills → missão ainda ativa  ✓")

        # Kill final: completa a missão
        mgr.record_kill(target_faction)
        assert mission.id not in mgr.active_missions
        assert mission.id in mgr.completed_missions
        assert mission.status == MissionStatus.COMPLETED
        assert credits_received == [mission.reward_credits], \
            f"ADD_CREDITS esperado {[mission.reward_credits]}, recebido {credits_received}"
        print(f"  {required}/{required} kills → missão completa, "
              f"+{mission.reward_credits} cr emitido  ✓")
    finally:
        bus.unsubscribe("ADD_CREDITS", credits_received.append)

    # ------------------------------------------------------------------
    # 3) Kills de facção errada não contam
    # ------------------------------------------------------------------
    print("\n[3] Kills de facção errada não contam")
    mgr2 = MissionManager()
    mgr2.set_templates(bounty_templates)

    m2 = mgr2.generate_mission(faction="United Humans")
    mgr2.accept_mission(m2.id)
    kill_obj2 = next(o for o in m2.objectives if o.get("type") == "KILL")
    target_faction2 = kill_obj2["target_faction"]

    mgr2.record_kill("Independent")  # facção errada
    assert m2.kill_progress == 0
    assert m2.id in mgr2.active_missions
    print(f"  Kill de 'Independent' para missão contra '{target_faction2}' → 0 progresso  ✓")

    # ------------------------------------------------------------------
    # 4) Múltiplas missões rastreadas independentemente
    # ------------------------------------------------------------------
    print("\n[4] Múltiplas missões rastreadas independentemente")
    mgr3 = MissionManager()
    mgr3.set_templates(bounty_templates)

    m_a = mgr3.generate_mission(faction="United Humans")
    m_b = mgr3.generate_mission(faction="United Humans")
    mgr3.accept_mission(m_a.id)
    mgr3.accept_mission(m_b.id)

    kill_obj_a = next(o for o in m_a.objectives if o.get("type") == "KILL")
    target_faction_a = kill_obj_a["target_faction"]
    required_a = kill_obj_a["count"]

    credits_multi = []
    bus.subscribe("ADD_CREDITS", credits_multi.append)
    try:
        # Kills suficientes para completar m_a (e m_b, se mesmo alvo e count)
        for _ in range(required_a):
            mgr3.record_kill(target_faction_a)

        assert m_a.id in mgr3.completed_missions, "Missão A não completou"
        assert m_a.kill_progress >= required_a
        # Missão B também rastreou os mesmos kills (mesmo target_faction)
        assert m_b.kill_progress == required_a
        print(f"  Após {required_a} kills: missão A completa, "
              f"missão B com {m_b.kill_progress} kills registrados  ✓")
        assert len(credits_multi) >= 1, "Nenhum ADD_CREDITS emitido"
        print(f"  {len(credits_multi)} evento(s) ADD_CREDITS emitido(s)  ✓")
    finally:
        bus.unsubscribe("ADD_CREDITS", credits_multi.append)

    print("\nTeste do Mission Loop: OK")


if __name__ == "__main__":
    main()
