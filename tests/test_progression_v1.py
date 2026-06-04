"""
Teste de progressão e condição de vitória (Ciclo E).

Cobre:
  1. Contador de bounties começa em 0 e só incrementa com BOUNTY completados.
  2. GAME_COMPLETED emitido ao atingir WIN_BOUNTY_COUNT; não reemitido depois.
  3. Missões não-BOUNTY não contam para o objetivo de vitória.
  4. Round-trip: salvar com progresso → menu → carregar → estado idêntico.
  5. Persistência do flag game_completed: carregar um save "já ganho" restaura
     o estado sem reemitir GAME_COMPLETED.
"""
import os
import sys
import tempfile

os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.event_bus import bus
from core.save_manager import SaveManager
from systems.progression_manager import ProgressionManager, WIN_BOUNTY_COUNT
from main_pygame import SpaceRPGVisual


# ---------------------------------------------------------------------------
# Auxiliares
# ---------------------------------------------------------------------------

def _fresh_game(tmpdir):
    game = SpaceRPGVisual()
    game.save_mgr = SaveManager(save_dir=tmpdir)
    game.main_menu_ui.open(game._has_saves())
    return game


def _emit_bounty(n: int = 1):
    """Emite n eventos MISSION_COMPLETED do tipo BOUNTY."""
    for _ in range(n):
        bus.emit("MISSION_COMPLETED", {
            "type": "BOUNTY",
            "reward_credits": 1000,
        })


# ---------------------------------------------------------------------------
# Testes
# ---------------------------------------------------------------------------

def main():
    print("=" * 60)
    print("Teste de Progressão e Fim de Jogo (Ciclo E)")
    print("=" * 60)

    # ------------------------------------------------------------------
    # 1) Contador inicia em zero; só bounties contam
    # ------------------------------------------------------------------
    print(f"\n[1] Progresso inicial: 0/{WIN_BOUNTY_COUNT}")
    tmpdir = tempfile.mkdtemp(prefix="space_rpg_prog_")
    game = _fresh_game(tmpdir)
    game.start_new_game("Pilot E")

    assert game.prog_mgr is not None
    assert game.prog_mgr.bounties_completed == 0
    assert not game.prog_mgr.game_completed
    print(f"  ✓ bounties_completed = 0, game_completed = False")

    # Missão de outro tipo não conta
    bus.emit("MISSION_COMPLETED", {"type": "DELIVERY", "reward_credits": 500})
    assert game.prog_mgr.bounties_completed == 0
    print("  ✓ DELIVERY não incrementa bounties_completed")

    # ------------------------------------------------------------------
    # 2) WIN_BOUNTY_COUNT bounties → GAME_COMPLETED emitido exatamente uma vez
    # ------------------------------------------------------------------
    print(f"\n[2] {WIN_BOUNTY_COUNT} bounties → GAME_COMPLETED")
    completed_events = []
    bus.subscribe("GAME_COMPLETED", lambda d: completed_events.append(d))

    _emit_bounty(WIN_BOUNTY_COUNT - 1)
    assert game.prog_mgr.bounties_completed == WIN_BOUNTY_COUNT - 1
    assert not game.prog_mgr.game_completed
    assert len(completed_events) == 0
    print(f"  ✓ {WIN_BOUNTY_COUNT - 1} bounties: ainda não terminou")

    _emit_bounty(1)  # trigga a vitória
    assert game.prog_mgr.bounties_completed == WIN_BOUNTY_COUNT
    assert game.prog_mgr.game_completed
    assert len(completed_events) == 1
    assert game.game_state == "endgame", game.game_state
    print(f"  ✓ GAME_COMPLETED emitido 1 vez, game_state = 'endgame'")

    # Mais bounties não reemitem
    _emit_bounty(3)
    assert len(completed_events) == 1
    print("  ✓ Bounties extras não reemitem GAME_COMPLETED")

    # ------------------------------------------------------------------
    # 3) Round-trip save/load preserva estado de progressão
    # ------------------------------------------------------------------
    print("\n[3] Round-trip: salvar com progresso → menu → carregar")
    game.game_state = "playing"   # sair do endgame para salvar
    game._save_game()
    game._go_main_menu()
    assert game.prog_mgr is None, "prog_mgr deveria ser None no menu"

    entries = game._save_entries()
    assert len(entries) == 1
    ok = game.load_game(entries[0]["slot"])
    assert ok
    assert game.prog_mgr.bounties_completed == WIN_BOUNTY_COUNT
    assert game.prog_mgr.game_completed
    print(f"  ✓ Após carregar: bounties={game.prog_mgr.bounties_completed}, "
          f"completed={game.prog_mgr.game_completed}")

    # ------------------------------------------------------------------
    # 4) Carregar save "já ganho" não reemite GAME_COMPLETED
    # ------------------------------------------------------------------
    print("\n[4] Carregar save já ganho não reemite GAME_COMPLETED")
    events_before = len(completed_events)
    game._go_main_menu()
    game.load_game(entries[0]["slot"])
    assert len(completed_events) == events_before, \
        f"GAME_COMPLETED reemitido ao carregar ({len(completed_events)} eventos)"
    print("  ✓ load_game não reemite GAME_COMPLETED para save já ganho")

    print("\nTeste de progressão: OK")


if __name__ == "__main__":
    main()
