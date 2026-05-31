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

## Sistema de movimento da nave

O `PlayerManager` (`systems/player_manager.py`) aplica física vetorial por frame via EventBus.

### Empuxo (hierarquia de força)

| Ação | Constante | Força relativa |
|---|---|---|
| Motor principal (frente) | `thrust_power = 3000 N` | 100% |
| Ré | `reverse_power = 1650 N` | 55% |
| Strafe lateral (RCS) | `strafe_power = 1350 N` | 45% |

Todos os valores escalam pelo modificador de pips de engines:
`engine_mod = 0.5 + (pips["engines"] / 4.0) * 0.5` (50% a 100%).

### Throttle estilo Elite Dangerous (W / S)

`thrust_value > 0` → motor principal empurra na direção do bico.
`thrust_value < 0` → empuxo na direção **oposta** ao bico com a força de ré.
Partindo de velocidade frontal positiva, `S` primeiro **freia** e, ao cruzar
o ponto morto (velocidade zero), **engata a ré**.

### Strafe (Q / E)

`strafe()` calcula o vetor perpendicular ao bico (`right = (-fy, fx)`) e aplica
o empuxo lateral **sem alterar `ship.rotation`**. Q = esquerda, E = direita.

### Drag (atrito de jogabilidade)

```python
drag = 0.997
velocity *= drag ** (dt * 60)   # ~17 % de perda por segundo a 60 fps
```

Velocidade de cruzeiro resultante (Skiff, massa 120): ~150 unidades/s.

---

## Poder de fogo por hardpoints

As naves declaram `hardpoints` no `data/ships.json`
(`weapon_small/medium/large`, `utility`). Esse campo agora é propagado para o
`Ship` (campo `hardpoints`), via `Ship.from_dict` e `UniverseManager.spawn_ship`.

O `CombatManager` deriva o **multiplicador de dano por disparo** dos hardpoints
de arma (`CombatManager.hardpoint_firepower`):

```
firepower = weapon_small*1 + weapon_medium*3 + weapon_large*9   (fallback 1.0)
```

Cada porte vale ~3× o anterior. `fire()` multiplica `proj.damage` por esse
valor — vale para player **e** NPCs (ambos passam por `fire`). Naves sem
hardpoint de arma usam `1.0` (nunca zera o dano nem crasha).

| Nave | Hardpoints | firepower |
|---|---|---|
| Skiff | 2S | x2 |
| Wasp | 4S + 1M | x7 |
| Mule | 1S + 1M | x4 |
| Albatross | 1S | x1 |

Escopo deliberadamente simples (sem sistema de módulos — ver ADR 001): o
armamento é derivado dos hardpoints já declarados, não de Modules equipados.
O painel do mercado (`StationUI`) mostra a linha "PODER DE FOGO".

---

## Executar e testar

```bash
pip install pygame Pillow          # dependências
python main_pygame.py              # versão visual
SDL_VIDEODRIVER=dummy python main_pygame.py   # smoke headless (sem janela)

# Testes (cada um roda direto, sem framework):
python tests/test_docking.py
python tests/test_movement.py
python tests/test_input_config.py
python tests/test_combat.py
python tests/test_economy_loop.py
python tests/test_hardpoints.py
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

| Estado | Descrição |
|---|---|
| `"playing"` | Gameplay normal; inputs contínuos ativos |
| `"paused"` | Menu de pausa (CONTINUAR / CONFIGURAR TECLAS / SAIR DO JOGO) |
| `"keybinds"` | Tela de remapeamento de teclas; todos os eventos vão para `KeybindsUI` |
| `"docked"` | UI da estação aberta; lógica de jogo pausada |
| `"dying"` | Animação de morte (3 s) antes do respawn |

Regras de transição importantes:
- A tecla de pausa (configurável) só abre o menu durante `"playing"`.
- ESC **nunca fecha o jogo diretamente** — sair exige "SAIR DO JOGO" no menu de pausa.
- Desacoplar (F no menu da estação) faz transição direta `"docked"` → `"playing"` sem ambiguidade.

### Como adicionar uma nova ação remapeável

1. Adicione a entrada em `InputConfig.DEFAULTS` e em `InputConfig.LABELS`.
2. Em `main_pygame.py`, consuma a ação via `self._key("nova_acao")` no
   `_handle_input`. Pronto — a UI de rebind a lista automaticamente.
