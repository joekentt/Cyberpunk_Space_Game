"""
Teste do fluxo de menu (Ciclo D), headless via SDL_VIDEODRIVER=dummy.

A UI em si (desenho) é difícil de testar sem janela, então focamos a LÓGICA:
  1. O jogo NÃO spawna o mundo no init — abre em "main_menu", sem player.
  2. start_new_game("Nome") cria o player, registra o piloto e vai p/ "playing".
  3. Round-trip com o Ciclo C: novo jogo → muda estado → salvar → voltar ao
     menu → carregar → estado e nome do piloto restaurados.
  4. Anti-listener-duplicado: iniciar novo jogo duas vezes não acumula
     listeners no bus global (um ADD_CREDITS é processado UMA vez).
"""
import os
import sys
import tempfile

# Headless ANTES de importar pygame/main
os.environ.setdefault("SDL_VIDEODRIVER", "dummy")

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.event_bus import bus
from core.save_manager import SaveManager
import main_pygame
from main_pygame import SpaceRPGVisual


def _fresh_game(tmpdir):
    """Cria o jogo (menu) com SaveManager apontando para um dir temporário."""
    game = SpaceRPGVisual()
    game.save_mgr = SaveManager(save_dir=tmpdir)
    return game


def main():
    print("=" * 60)
    print("Teste de Fluxo de Menu (Ciclo D)")
    print("=" * 60)

    tmpdir = tempfile.mkdtemp(prefix="space_rpg_menu_")
    game = _fresh_game(tmpdir)

    # ------------------------------------------------------------------
    # 1) Boot no menu, sem mundo
    # ------------------------------------------------------------------
    print("\n[1] Boot no menu principal (sem mundo)")
    assert game.game_state == "main_menu", game.game_state
    assert game.player_id is None, "não deveria haver player no boot"
    assert game.universe is None, "o mundo não deveria existir no boot"
    print("  ✓ game_state == 'main_menu', sem player, sem universo")

    # ------------------------------------------------------------------
    # 2) start_new_game cria o mundo e registra o piloto
    # ------------------------------------------------------------------
    print("\n[2] start_new_game('Nova Pilota')")
    game.start_new_game("Nova Pilota")
    assert game.game_state == "playing", game.game_state
    assert game.player_id in game.universe.entities, "player não foi criado"
    assert game.pilot_name == "Nova Pilota", game.pilot_name
    player = game.universe.entities[game.player_id]
    assert player.is_player and player.faction == "United Humans"
    print(f"  ✓ player criado, piloto '{game.pilot_name}', estado 'playing'")

    # ------------------------------------------------------------------
    # 3) Round-trip: muda estado → salvar → menu → carregar
    # ------------------------------------------------------------------
    print("\n[3] Round-trip salvar/menu/carregar (integra Ciclo C)")
    player.credits = 98765
    player.position = [1234.0, -567.0]
    player.current_hp = 33.0
    game.player_mgr.pips = {"weapons": 4, "shields": 1, "engines": 1}
    player.pips = dict(game.player_mgr.pips)

    game._save_game()                       # grava no slot único
    assert game._has_saves(), "save não foi detectado"

    game._go_main_menu()
    assert game.game_state == "main_menu"
    assert game.player_id is None and game.universe is None
    print("  ✓ salvou e voltou ao menu (mundo descartado)")

    # A lista de saves deve trazer o nome do piloto e os créditos
    entries = game._save_entries()
    assert len(entries) == 1, entries
    assert entries[0]["pilot"] == "Nova Pilota", entries[0]
    assert entries[0]["credits"] == 98765, entries[0]
    print(f"  ✓ menu de load lista: piloto '{entries[0]['pilot']}', "
          f"{entries[0]['credits']} cr")

    ok = game.load_game(entries[0]["slot"])
    assert ok, "load_game retornou False"
    assert game.game_state == "playing"
    rp = game.universe.entities[game.player_id]
    assert rp.credits == 98765, rp.credits
    assert abs(rp.position[0] - 1234.0) < 1e-4 and abs(rp.position[1] + 567.0) < 1e-4
    assert abs(rp.current_hp - 33.0) < 1e-6, rp.current_hp
    assert game.player_mgr.pips == {"weapons": 4, "shields": 1, "engines": 1}
    assert game.pilot_name == "Nova Pilota", game.pilot_name
    # managers reapontados para a nave reconstruída
    assert game.player_mgr.ship is rp and game.energy_mgr.ship is rp
    print("  ✓ estado e piloto restaurados após carregar")

    # ------------------------------------------------------------------
    # 4) Anti-listener-duplicado
    # ------------------------------------------------------------------
    print("\n[4] Iniciar novo jogo 2x não duplica listeners no bus")
    game.start_new_game("Teste A")
    game.start_new_game("Teste B")   # se acumulasse, ADD_CREDITS dispararia 2x

    p = game.universe.entities[game.player_id]
    before = p.credits
    n_listeners = len(bus._listeners.get("ADD_CREDITS", []))
    print(f"  listeners em ADD_CREDITS: {n_listeners} (esperado 1)")
    assert n_listeners == 1, f"listeners duplicados: {n_listeners}"

    bus.emit("ADD_CREDITS", 100)
    assert p.credits == before + 100, \
        f"ADD_CREDITS processado em duplicidade ({p.credits} != {before + 100})"
    print(f"  ✓ ADD_CREDITS processado UMA vez ({before} → {p.credits})")

    # Sanidade: o nome do piloto do segundo "novo jogo" venceu
    assert game.pilot_name == "Teste B", game.pilot_name

    print("\nTeste de fluxo de menu: OK")


if __name__ == "__main__":
    main()
