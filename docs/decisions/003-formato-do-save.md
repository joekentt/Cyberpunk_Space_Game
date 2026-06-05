# ADR 003 — Formato do save e fonte única de créditos

**Data:** 2026-06-03
**Status:** Aceito

## Contexto

O `SaveManager` (`core/save_manager.py`) já existia com escrita atômica
(`.tmp` + `shutil.move`), e dois sistemas já tinham serialização pronta
(`FactionManager` e `MissionManager`). Faltava: (1) serializar o **estado vivo**
da nave do jogador, distinto do template de catálogo (`ships.json`); (2) montar
um payload único versionado; (3) aplicá-lo no load reapontando os managers.

Ao desenhar o payload surgiram duas decisões que valem registro.

## Decisão

### 1. Campo `version` no topo do payload

Todo save carrega `"version": 1` (`SAVE_VERSION` em
`systems/game_state_serializer.py`). Isso permite, no futuro, detectar saves
antigos e migrá-los (ou rejeitá-los com mensagem clara) em vez de quebrar com
`KeyError` silencioso. O loader já lê e valida esse campo.

### 2. Fonte ÚNICA de verdade para créditos

Em runtime, os créditos do jogador vivem em `player_ship.credits`. No arquivo de
save, eles são gravados em **um só lugar**: o campo top-level `credits` do
payload. `Ship.to_save_dict()` deliberadamente **não** inclui créditos, então é
impossível o arquivo conter dois valores divergentes. No load, o serializer lê
`payload["credits"]` e o aplica de volta a `ship.credits`.

### 3. Estado vivo separado do template de catálogo

`Ship.from_dict()` (lê `ships.json`, chave `base_stats`) continua intacto para
spawnar naves novas. O caminho de save usa um par novo e distinto —
`Ship.to_save_dict()` / `Ship.from_save_dict()` — que captura o estado de
runtime: `position`, `velocity`, `rotation`, `current_hp/max_hp`,
`current_shields/max_shields`, `current_heat`, `faction`, `model_id`,
`hardpoints`, etc. Misturar os dois formatos seria fonte de bugs (HP cheio ao
carregar, posição perdida, etc.).

## Formato do payload

```json
{
  "version": 1,
  "player_ship": { "model_id": "...", "position": [x, y], "rotation": 0.0,
                   "current_hp": 0.0, "current_shields": 0.0, "...": "..." },
  "pips": {"weapons": 2, "shields": 2, "engines": 2},
  "credits": 0,
  "missions": { "active": {}, "completed": [] },
  "factions": { "reputation_axes": {}, "historical_flags": [], "diplomacy": {} },
  "last_docked_station_id": "station_alpha",
  "camera_offset": [0.0, 0.0]
}
```

## Consequências

### Positivas
- Sem duplicação de créditos → impossível divergir no arquivo.
- `version` abre caminho para migração de saves entre ciclos.
- `to_save_dict`/`from_save_dict` isolam o estado vivo; o template de catálogo
  (`from_dict`) fica intocado.
- Funções puras em `game_state_serializer.py` (recebem managers por parâmetro)
  → testáveis headless sem pygame (`tests/test_save_load.py`).

### Negativas / limites deste ciclo
- **Slot único** (slot 1). UI navegável multi-slot é do Ciclo D.
- O load é disparado por tecla de debug (F9); o menu principal que consome
  `load_game()` é do Ciclo D. A função já está pública e pronta.
- Estado do mundo (NPCs, posição de inimigos, inventário das estações) **não** é
  persistido — apenas o estado do jogador, missões e reputação, conforme o
  critério de conclusão do Ciclo C.

## Implementação

- `entities/ship.py`: `to_save_dict()` / `from_save_dict()` (estado vivo).
- `systems/game_state_serializer.py` (novo): `build_save_payload()` /
  `apply_save_payload()`, `SAVE_VERSION`.
- `main_pygame.py`: `FactionManager` + `SaveManager` instanciados; opção
  "SALVAR JOGO" no menu de pausa; `load_game()` público (debug em F9).
- `tests/test_save_load.py` (novo): grava num `tempfile.mkdtemp`, recarrega em
  managers zerados e confere campo a campo.
