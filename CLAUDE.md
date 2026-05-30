# CLAUDE.md

Orientações para trabalhar neste repositório (Cyberpunk Space RPG).

## Visão geral

RPG espacial 2D top-down em Python. Arquitetura desacoplada por um **EventBus**
central (`core/event_bus.py`): os sistemas se comunicam emitindo/ouvindo eventos
em vez de se referenciarem diretamente.

```
core/        EventBus, SaveManager, InputConfig, DataLoader, GameLoop
systems/     Managers (player, npc, combat, station, energy, economy...)
entities/    Ship, Module, Station (dataclasses puras, sem pygame)
visual_engine/  Geração procedural de sprites, HUD, Camera, StationUI, KeybindsUI
data/        ships.json, factions.json, mission_templates.json
config/      keybinds.json (gerado em runtime — keybindings do jogador)
saves/       slots de save (gerados em runtime)
tests/       testes executáveis diretamente (headless)
main_pygame.py   entry-point visual (Pygame)
main.py          entry-point console
```

## Executar e testar

```bash
pip install pygame Pillow          # dependências
python main_pygame.py              # versão visual
SDL_VIDEODRIVER=dummy python main_pygame.py   # smoke headless (sem janela)

# Testes (cada um roda direto, sem framework):
python tests/test_docking.py
python tests/test_movement.py
python tests/test_input_config.py
```

Os testes em `tests/` que cobrem lógica pura (movimento, docking, input config)
**não dependem de pygame** e devem passar em qualquer ambiente. Ao mexer em
lógica de gameplay, prefira validar por um teste headless em `tests/`.

## Sistema de input (keybindings configuráveis)

O mapeamento ação → tecla é configurável pelo jogador e persistido em disco.

### `core/input_config.py` — `InputConfig`

- Módulo **puro** (sem pygame) para ser testável headless.
- Mantém `bindings`: dicionário `ação -> nome_de_tecla`, onde o nome segue o
  formato do pygame (`pygame.key.name(code)`): `"w"`, `"space"`, `"escape"`,
  `"left ctrl"` etc.
- **Ações** (em `DEFAULTS`, nesta ordem): `thrust_forward`, `thrust_back`,
  `rotate_left`, `rotate_right`, `strafe_left`, `strafe_right`, `shoot`,
  `dock_toggle`, `pause`.
- **Padrões:** W, S, A, D, Q, E, ESPAÇO, F, ESC.
- API principal: `get(action)`, `set(action, key_name)`, `conflicts()`
  (retorna `{tecla: [ações]}` para teclas usadas por mais de uma ação),
  `reset_to_defaults()`, `load()`, `save()`.
- **Persistência:** `config/keybinds.json`, escrita **atômica** (arquivo `.tmp`
  + `os.replace`), no mesmo espírito do `SaveManager`.
- **Tolerância a falhas:** se o arquivo não existir ou estiver corrompido,
  os padrões são usados e o input nunca quebra. O arquivo só é criado no
  primeiro `save()` (ou seja, ao rebindar algo).

### `config/keybinds.json`

Gerado em runtime; **não versionado** (está no `.gitignore`, pois é dado do
usuário). Exemplo:

```json
{
    "thrust_forward": "w",
    "thrust_back": "s",
    "rotate_left": "a",
    "rotate_right": "d",
    "strafe_left": "q",
    "strafe_right": "e",
    "shoot": "space",
    "dock_toggle": "f",
    "pause": "escape"
}
```

### Consumo em `main_pygame.py`

- Em `__init__`, cria `self.input_cfg = InputConfig()` e chama
  `self._rebuild_keymap()`, que monta `self._keymap: ação -> keycode pygame`
  via `pygame.key.key_code(nome)`. Nomes inválidos caem no default da ação.
- `_handle_input` **não tem mais teclas hardcoded** para gameplay: usa
  `self._key("thrust_forward")` etc. para comparar com os eventos/estado das
  teclas. (As teclas de UI fixas — ENTER, setas, dígitos 1/2/3 dos pips —
  seguem fixas de propósito.)
- Ao rebindar, a `KeybindsUI` chama o callback `on_change=self._rebuild_keymap`,
  então o novo bind passa a valer **imediatamente**, sem reiniciar o jogo.

### `visual_engine/keybinds_ui.py` — `KeybindsUI`

Tela de remapeamento acessível pelo **menu de pausa** (estado de jogo
`"keybinds"`). Controles: `↑↓` navega, `ENTER` inicia o rebind (a próxima
tecla vira o bind), `ESC` volta / cancela, `BACKSPACE` restaura padrões,
clique do mouse seleciona e já inicia o rebind. Conflitos são destacados em
vermelho e avisados por mensagem. `handle_event` devolve `"close"` quando o
jogador sai da tela (o loop então volta para `"paused"`).

### Estados de jogo (`self.game_state`)

`"playing"` | `"paused"` | `"keybinds"` | `"docked"` | `"dying"`. A tecla de
pausa (configurável) só abre o menu durante `"playing"`; ESC nunca fecha o
jogo diretamente — sair exige a opção "SAIR DO JOGO" no menu de pausa.

### Como adicionar uma nova ação remapeável

1. Adicione a entrada em `InputConfig.DEFAULTS` e em `InputConfig.LABELS`.
2. Em `main_pygame.py`, consuma a ação via `self._key("nova_acao")` no
   `_handle_input`. Pronto — a UI de rebind a lista automaticamente.
