"""
game_state_serializer — monta e aplica o payload de save/load completo.

Mantém o `main_pygame.py` enxuto: toda a lógica de "como o estado do jogo vira
um dict serializável (e vice-versa)" vive aqui, em funções puras que recebem os
managers por parâmetro. Isso também torna o caminho testável headless (sem
pygame) — ver `tests/test_save_load.py`.

Formato do payload (ver docs/decisions/003-formato-do-save.md):

    {
      "version": 2,
      "pilot": {"name": str},         # Ciclo D: identidade do piloto
      "saved_at": float,              # epoch do save (exibição no menu de load)
      "player_ship": {... estado vivo da nave ...},
      "pips": {"weapons": int, "shields": int, "engines": int},
      "credits": int,                 # ÚNICA fonte de verdade dos créditos
      "missions": {... MissionManager.get_save_data() ...},
      "factions": {... FactionManager.get_save_data() ...},
      "last_docked_station_id": str | null,
      "camera_offset": [x, y]
    }

DECISÃO DE DESIGN — fonte única de créditos:
  Os créditos do jogador vivem em `player_ship.credits` em runtime, mas no save
  são gravados em UM só lugar: o campo top-level `credits`. `Ship.to_save_dict()`
  deliberadamente NÃO inclui créditos, então não há risco de dois valores
  divergirem no arquivo.

VERSÃO 2 (Ciclo D): acrescenta `pilot` e `saved_at`. São campos aditivos e
opcionais no load (`.get` com default), então saves v1 continuam carregáveis.
"""
import time
from typing import Any, Dict, Optional

from entities.ship import Ship

SAVE_VERSION = 2


def build_save_payload(player_ship: Ship,
                       pips: Dict[str, int],
                       mission_mgr,
                       faction_mgr,
                       last_docked_station_id: Optional[str] = None,
                       camera_offset=None,
                       pilot: Optional[Dict[str, Any]] = None,
                       progression: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    """
    Monta o dict de save completo a partir do estado vivo dos managers.

    `pips` é a distribuição weapons/shields/engines (fonte: PlayerManager.pips).
    `credits` é extraído de `player_ship.credits` (fonte única de verdade).
    `pilot` é a identidade do piloto (Ciclo D); default {"name": "Piloto"}.
    `progression` é o estado do ProgressionManager (Ciclo E); campo aditivo.
    """
    return {
        "version": SAVE_VERSION,
        "pilot": dict(pilot) if pilot else {"name": "Piloto"},
        "saved_at": time.time(),
        "player_ship": player_ship.to_save_dict(),
        "pips": dict(pips),
        "credits": int(player_ship.credits),
        "missions": mission_mgr.get_save_data(),
        "factions": faction_mgr.get_save_data(),
        "last_docked_station_id": last_docked_station_id,
        "camera_offset": list(camera_offset) if camera_offset else [0.0, 0.0],
        "progression": dict(progression) if progression else {},
    }


def apply_save_payload(payload: Dict[str, Any],
                       universe,
                       player_mgr,
                       energy_mgr,
                       mission_mgr,
                       faction_mgr,
                       station_mgr=None,
                       old_player_id: Optional[str] = None) -> str:
    """
    Reconstrói o estado de jogo a partir de um payload e reaponta os managers.

    Segue o mesmo padrão de `_on_ship_purchased`/`_respawn` no main_pygame:
    remove a nave antiga, spawna a nova e reaponta `player_mgr.ship` /
    `energy_mgr.ship`. Retorna o novo `player_id`.
    """
    # 1) Remove a nave antiga do player, se houver.
    if old_player_id and old_player_id in universe.entities:
        universe.remove_entity(old_player_id)

    # 2) Reconstrói a nave do estado vivo e aplica a fonte única de créditos.
    ship_state = payload["player_ship"]
    template = Ship.from_save_dict(ship_state)
    template.is_player = True
    template.credits = int(payload.get("credits", 0))

    # 3) Spawn no universo. spawn_ship zera velocity/rotation/heat (clona um
    #    template "novo"), então restauramos esses campos vivos logo em seguida.
    new_id = universe.spawn_ship(template, ship_state.get("position", [0.0, 0.0]))
    new_player = universe.entities[new_id]
    new_player.velocity = list(ship_state.get("velocity", [0.0, 0.0]))
    new_player.rotation = ship_state.get("rotation", 0.0)
    new_player.current_heat = ship_state.get("current_heat", 0.0)
    new_player.credits = int(payload.get("credits", 0))

    # 4) Reaponta managers para a nova nave.
    player_mgr.ship = new_player
    energy_mgr.ship = new_player

    # 5) Restaura pips (PlayerManager, EnergyManager e o espelho em ship.pips).
    pips = dict(payload.get("pips", {"weapons": 2, "shields": 2, "engines": 2}))
    player_mgr.pips = dict(pips)
    if hasattr(energy_mgr, "pips"):
        energy_mgr.pips = dict(pips)
    new_player.pips = dict(pips)

    # 6) Missões e reputação.
    mission_mgr.load_save_data(payload.get("missions", {}))
    faction_mgr.load_save_data(payload.get("factions", {}))

    # 7) Última estação atracada (para respawn).
    if station_mgr is not None:
        station_mgr.last_docked_station_id = payload.get("last_docked_station_id")

    return new_id
