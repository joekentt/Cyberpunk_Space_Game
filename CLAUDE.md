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

### Boost (SHIFT)

Empuxo frontal de pico ativado por `{"action": "boost"}` via EventBus. Números
em `data/balance.json` → seção `boost` (ver ADR 007):

| Parâmetro | Valor padrão | Descrição |
|---|---|---|
| `force_mult` | 2.6× | Multiplicador do `thrust_power` durante o pico |
| `duration` | 0.8 s | Duração do empuxo de boost |
| `cost` | 1.0 | Carga consumida por ativação |
| `max_charge` | 3.0 | Capacidade total do capacitor |
| `recharge_per_s` | 0.5/s | Recarga (escala com `engine_mod`) |
| `cooldown` | 0.4 s | Espera adicional após o fim do pico |

`PlayerManager.try_boost()` ativa se `_boost_cd <= 0`, `_boost_timer <= 0` e
`boost_charge >= cost`. Dentro de `update()`, se `_boost_timer > 0`, aplica
`_apply_boost_thrust(dt)` **independentemente de o jogador segurar W** — dá
a sensação de "kick". Só afeta o eixo frontal; ré e strafe inalterados.

O estado do capacitor é espelhado em `ship.boost_charge / ship.boost_max` para
a HUD (`hud.py`). Ao recriar a Ship (`_on_ship_purchased`, `_respawn`),
`PlayerManager.ship` é reapontado e o espelho é re-sincronizado no próximo
`update()` (sem reset manual necessário).

### Drag (atrito de jogabilidade)

```python
drag = 0.997
velocity *= drag ** (dt * 60)   # ~17 % de perda por segundo a 60 fps
```

Velocidade de cruzeiro resultante (Skiff, massa 120): ~150 unidades/s.
Com boost, velocidade de pico temporária acima desse teto; o drag traz de volta
naturalmente em poucos segundos (sem clamp rígido).

---

## Poder de fogo por hardpoints

As naves declaram `hardpoints` no `data/ships.json`
(`weapon_small/medium/large`, `utility`). Esse campo agora é propagado para o
`Ship` (campo `hardpoints`), via `Ship.from_dict` e `UniverseManager.spawn_ship`.

O `CombatManager` deriva o **multiplicador de dano por disparo** dos hardpoints
de arma (`CombatManager.firepower_from_hardpoints`). Os pesos e o expoente são
**data-driven** (`data/balance.json` → seção `firepower`; ver ADR 004):

```
raw       = weapon_small*1 + weapon_medium*2 + weapon_large*4
firepower = raw ** 0.6                                   (fallback 1.0)
```

O expoente `0.6` **achata a curva** (Ciclo B): comprar uma nave melhor é
perceptível mas não esmagador. `fire()` multiplica `proj.damage` por esse
valor — vale para player **e** NPCs (ambos passam por `fire`). Naves sem
hardpoint de arma usam `1.0` (nunca zera o dano nem crasha).

| Nave | Hardpoints | raw | firepower |
|---|---|---|---|
| Skiff | 2S | 2 | x1.52 |
| Wasp | 4S + 1M | 6 | x2.93 |
| Stingray | 3S + 1M | 5 | x2.63 |
| Mule | 1S + 1M | 3 | x1.93 |
| Albatross | 1S | 1 | x1.00 |
| Terraformador | 1S | 1 | x1.00 |

A melhor nave de combate Tier 1 (Wasp) tem ~1.9× a ofensiva da Skiff (antes era
3.5×). Escopo deliberadamente simples (sem sistema de módulos — ver ADR 001): o
armamento é derivado dos hardpoints já declarados, não de Modules equipados.
O painel do mercado (`StationUI`) mostra a linha "PODER DE FOGO" usando o mesmo
helper (`CombatManager.firepower_from_hardpoints`) — fonte única da fórmula.

### Balanceamento data-driven (`data/balance.json`)

Números de combate ficam em `data/balance.json`, carregado por `core/balance.py`
(singleton `balance`, **tolerante a falhas**: usa `DEFAULTS` se o arquivo faltar
ou corromper, no espírito do `InputConfig`). Seções:

- `firepower`: pesos por porte + `exponent` + `fallback`.
- `ai`: `attack_range`, `detection_range`, `fire_chance_per_tick`,
  `flee_shield_threshold` (=0 → piratas Tier 1 lutam até o fim),
  `recover_shield_threshold`.
- `shield`: `base_recharge` (recarga de escudo do player, escala com pips).

Consumidores: `CombatManager` (firepower), `NPCManager` (IA), `EnergyManager`
(recarga). Tuning de balanceamento não exige editar código.

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
python tests/test_combat_balance.py   # duelo justo Skiff vs pirata (Ciclo B)
python tests/test_economy_loop.py
python tests/test_hardpoints.py
python tests/test_save_load.py
python tests/test_menu_flow.py        # menu, criação de piloto, novo/carregar (Ciclo D)
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
  `rotate_left`, `rotate_right`, `strafe_left`, `strafe_right`, `boost`,
  `shoot`, `dock_toggle`, `pause`.
- **Padrões:** W, S, A, D, Q, E, SHIFT, ESPAÇO, F, ESC.
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
| `"main_menu"` | Menu principal — **estado inicial**; o mundo ainda não existe |
| `"pilot_creation"` | Tela de criação de piloto (digita o nome → `start_new_game`) |
| `"load_menu"` | Lista de saves; ENTER chama `load_game(slot)` |
| `"playing"` | Gameplay normal; inputs contínuos ativos |
| `"paused"` | Menu de pausa (CONTINUAR / SALVAR / SALVAR E SAIR PARA O MENU / TECLAS / SAIR) |
| `"keybinds"` | Tela de remapeamento; `_keybinds_return` diz se volta a `"paused"` ou `"main_menu"` |
| `"docked"` | UI da estação aberta; lógica de jogo pausada |
| `"dying"` | Animação de morte (3 s) antes do respawn |

Regras de transição importantes:
- O jogo **abre em `"main_menu"`**; o mundo só é construído em `start_new_game`
  ou `load_game`. `__init__` NÃO spawna player/NPCs/estações.
- A tecla de pausa (configurável) só abre o menu durante `"playing"`.
- ESC **nunca fecha o jogo diretamente** — sair exige "SAIR DO JOGO" no menu de pausa.
- Desacoplar (F no menu da estação) faz transição direta `"docked"` → `"playing"` sem ambiguidade.

### Ciclo de vida do mundo e limpeza do EventBus (armadilha do singleton)

O `bus` (`core/event_bus.py`) é **global e singleton**, e os managers se
inscrevem no `__init__`. Recriar managers a cada "novo jogo"/"carregar" sem
limpar **acumularia listeners duplicados** (cada evento dispararia N vezes).

Solução adotada (ver ADR 005): toda (re)construção do mundo passa por
`SpaceRPGVisual._build_world_systems()`, que **limpa `bus._listeners` antes**
de recriar os managers e re-inscrever os handlers de `self` (`_subscribe_self`).
`_teardown_world()` (ao voltar ao menu) também limpa o bus e zera os managers.
Assim, iniciar novo jogo várias vezes mantém **exatamente um** listener por
evento (coberto por `tests/test_menu_flow.py`, item 4).

`start_new_game(pilot_name)` constrói o mundo do zero; `load_game(slot)`
reconstrói e aplica o save por cima (reusa o serializer do Ciclo C).

### Como adicionar uma nova ação remapeável

1. Adicione a entrada em `InputConfig.DEFAULTS` e em `InputConfig.LABELS`.
2. Em `main_pygame.py`, consuma a ação via `self._key("nova_acao")` no
   `_handle_input`. Pronto — a UI de rebind a lista automaticamente.
