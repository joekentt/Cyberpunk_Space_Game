# CLAUDE.md

Orientações para trabalhar neste repositório (Cyberpunk Space RPG).

## Visão geral

RPG espacial 2D top-down em Python. Arquitetura desacoplada por um **EventBus**
central (`core/event_bus.py`): os sistemas se comunicam emitindo/ouvindo eventos
em vez de se referenciarem diretamente.

```
core/        EventBus, SaveManager, InputConfig, DataLoader, GameLoop
systems/     Managers (player, npc, combat, station, energy, audio, supercruise...)
entities/    Ship, Module, Station (dataclasses puras, sem pygame)
visual_engine/  Geração procedural de sprites, HUD, Radar, Camera, StationUI, KeybindsUI
data/        ships.json, factions.json, balance.json, audio.json
assets/audio/  WAVs de SFX (placeholders sintéticos versionados)
tools/       utilitários (gen_placeholder_sfx.py)
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
- `boost`: ver seção **Boost** acima (`force_mult`, `duration`, `cost`,
  `max_charge`, `recharge_per_s`, `cooldown`).
- `radar`: `range` (alcance do radar em unidades de mundo — ver seção **Radar**).
- `supercruise`: `speed_mult`, `max_speed`, `accel`, `spool_up_s`, `drop_radius`,
  `exit_offset`, `min_entry_distance` (ver seção **Supercruise** e ADR 010).
- `exploration`: `discover_radius`, `location_drop_chance`, `cartography_price`,
  `cartography_reveal_count` (ver seção **Exploração** e ADR 011).

Consumidores: `CombatManager` (firepower), `NPCManager` (IA), `EnergyManager`
(recarga), `PlayerManager` (boost), `Radar` (range), `SupercruiseManager`
(viagem), `ExplorationManager`/`LootManager`/`StationUI` (exploração). Tuning
de balanceamento não exige editar código.

---

## Radar de proximidade (ver ADR 008)

Overlay de HUD circular (estilo Elite) no canto inferior direito, com o player
no centro. É **puramente de apresentação**: lê posições já existentes
(`universe.entities`, `station_mgr.get_all()`) e desenha blips — não toca lógica
de jogo.

- `visual_engine/radar_math.py` — **puro, sem pygame**, testável headless.
  `radar_project(player_pos, target_pos, world_range, disc_radius)` devolve
  `(dx, dy, on_edge, in_range)` em pixels relativos ao centro do disco. Alvos
  fora do alcance são **clampados na borda** (mantêm a direção).
- `visual_engine/radar.py` — classe `Radar` (só desenha). Norte do radar = **+Y
  do mundo** (norte fixo, não alinhado à proa — mais estável ao manobrar).
- Cores por relação (mesma paleta do HUD de combate): **hostil = vermelho**,
  **neutro = amarelo**, **aliado = ciano**, **estação = verde (quadrado)**,
  **player = branco**. Blips fora do alcance ficam mais apagados.
- Toggle pela ação remapeável `toggle_radar` (padrão `R`), estado `_radar_on`
  em `main_pygame.py`. Desenhado no `_render` durante `"playing"`/`"paused"`.
- O alcance do radar (`balance.radar["range"]`) **não** é o alcance de detecção
  da IA (`balance.ai["detection_range"]`): ver um blip não significa que a nave
  já te detectou.
- Quando entidades/objetos novos (corpos celestes etc.) forem adicionados como
  entidades com `position`, o radar os inclui **automaticamente**.

### Fonte única de hostilidade — `systems/factions_util.py`

Para não duplicar a tabela de hostilidade numa terceira cópia, o set canônico
`HOSTILITY` e os helpers vivem aqui (módulo puro):

- `is_hostile(a, b)` — **direcional** `(atacante, alvo)`; semântica usada pela IA.
- `relation(viewer, other)` — **simétrica**; devolve `"hostile"` / `"ally"` /
  `"neutral"` para a coloração do radar.

`NPCManager.HOSTILITY` virou alias deste módulo e `CombatManager.hostility_table`
é derivado dele (comportamento inalterado, coberto por `tests/test_combat.py`).

---

## Supercruise (viagem rápida intra-setor — ver ADR 010)

Modo de voo de altíssima velocidade (~40× o cruzeiro) com drop automático ao se
aproximar de massa. É um `game_state` próprio (`"supercruise"`), **não** um
modificador do voo normal.

- `systems/supercruise_manager.py` — **lógica pura, sem pygame nem game_state**.
  `step(player, masses, dt)` acelera o player ao longo da proa até `max_speed`,
  integra a posição (`player.apply_physics`) e devolve um dict
  `{"drop", "drop_pos", "nearest", "distance", "speed"}`. `can_enter(pos, masses)`
  bloqueia entrada colado a massa. O manager **só faz contas**; quem decide as
  transições é o `main_pygame`.
- **Universo congelado exceto o player:** no branch `"supercruise"` do loop,
  `universe.update`/`npc_mgr`/`combat_mgr`/`station_mgr` **não** rodam. Logo,
  **sem dano e sem combate** durante a viagem. Só a rotação fica ativa (mira a
  proa) — aplicada via `player_mgr.rotate` direto, sem a física normal.
- **Entrada:** `supercruise_toggle` (padrão `J`) em `"playing"` inicia um
  spool-up (`_sc_spool`, `balance.supercruise["spool_up_s"]`), cancelável
  (apertar de novo). Ao zerar, `game_state = "supercruise"`.
- **Drop:** automático quando uma massa entra em `drop_radius` (reposiciona o
  player a `exit_offset` da massa, **fora do `docking_radius`** — não auto-acopla);
  ou manual via `J`/ESC. Emite `SUPERCRUISE_ENTER` / `SUPERCRUISE_DROP`.
- **Segurança numérica:** `exit_offset` (260) > maior `docking_radius` (180) e
  `drop_radius` (320) > `docking_radius` + margem. Coberto por
  `tests/test_supercruise.py` (caso 5: drop nunca dentro do raio de docking).
- O `SupercruiseManager` é **agnóstico a "setor"** — pronto para virar o
  transporte intra-setor natural quando o Plano 06 (multi-setor) chegar.

---

## Áudio por eventos (ver ADR 009)

`systems/audio_manager.py` (`AudioManager`) é um **consumidor puro de eventos**:
nenhum sistema de gameplay conhece áudio. Os managers já emitem eventos
(`WEAPON_FIRED`, `PROJECTILE_HIT`, `SHIP_DESTROYED`, `DOCKED`, `BOOST_ACTIVATED`,
`MISSION_COMPLETED`, `GAME_COMPLETED`, `PIPS_CHANGED`) e o `AudioManager` mapeia
**evento → som** via `data/audio.json`.

- **Tolerante a falhas:** sem `pygame.mixer` (CI/headless) → `enabled = False`,
  não carrega samples, mas ainda se inscreve no bus (inócuo). Arquivo faltando →
  entrada ignorada no load. `data/audio.json` ausente/corrompido → mapa vazio.
  Em nenhum caso crasha.
- **Divisão mixer × manager (armadilha):** `pygame.mixer.init()` roda **uma vez**
  no boot (`SpaceRPGVisual.__init__`, em try/except). O `AudioManager` é criado
  **por mundo** em `_build_world_systems` (logo após `bus._listeners.clear()`,
  regra do ADR 005) e zerado em `_teardown_world`. Como o clear roda antes,
  recriar o mundo (novo jogo 2×) **não duplica sons**.
- **Data-driven:** `data/audio.json` traz `master_volume` e, por evento,
  `file`/`volume`/`cooldown` (s). O `cooldown` evita empilhar samples (ex.: tiros).
- **Assets placeholder:** `tools/gen_placeholder_sfx.py` gera 8 WAVs sintéticos
  curtos com **stdlib pura** (sem numpy/pygame), versionados em `assets/audio/`
  para o jogo ter som "out of the box". Troque por arte final mantendo os nomes.
- **Testabilidade:** o manager aceita injeção de `play_fn` (default = tocar;
  teste = registrar chamadas) e `time_fn` (default = `time.monotonic`), então a
  lógica de mapa/cooldown é testada sem hardware (`tests/test_audio.py`).
- `set_master_volume()` / `toggle_mute()` já existem para uma futura UI de settings.

### Como adicionar um novo SFX

1. Coloque o WAV em `assets/audio/` (ou regere os placeholders).
2. Adicione a entrada `EVENTO: {"file": ..., "volume": ..., "cooldown": ...}`
   em `data/audio.json`. O `AudioManager` se inscreve naquele evento
   automaticamente — desde que algum sistema já o emita pelo bus.

---

## Exploração e mapa estelar (ver ADR 011)

**Escopo A:** o jogo continua em UM setor contínuo; o mapa mostra esse setor
com fog-of-war. Galáxia multi-sistema (Escopo B) ficou para um ciclo futuro.

- `entities/poi.py` — `PointOfInterest` (dados puros; `kind ∈ {station,
  asteroid_field, signal, derelict}`). POIs **não entram** em
  `universe.entities` — não poluem o universo de combate.
- `systems/exploration_manager.py` — dono dos POIs; **3 canais de descoberta**:
  1. **Proximidade:** `update(dt, player_pos)` dentro de `discover_radius`
     (roda em `"playing"` **e** `"supercruise"` — cruzar o setor revela o
     caminho). Emite `POI_DISCOVERED` **uma única vez** por POI, com `source`
     (`proximity`/`location_data`/`cartography`) para o feedback diferenciar.
  2. **Drop:** `LootManager` pode dropar `location_data`
     (`exploration.location_drop_chance`); o main chama
     `reveal_random_hidden()` — sem POI oculto é no-op.
  3. **Cartografia:** opção na `StationUI` debita créditos (fonte única,
     padrão do `_buy_ship`) e emite `CARTOGRAPHY_PURCHASED`; o manager revela
     `cartography_reveal_count` POIs.
- **Estados iniciais:** as 3 estações entram como POIs já descobertos
  (`register_station`); os 6 POIs ocultos vivem em `_setup_pois`.
- **Persistência aditiva:** campo `exploration` (`{"discovered_ids": [...]}`)
  no payload — saves antigos carregam com o default; IDs desconhecidos são
  ignorados. Segue o padrão do `progression`.
- **Starmap:** `visual_engine/starmap_math.py` (**puro**: `compute_bounds` +
  `world_to_map` com escala uniforme e clamp) e `starmap_ui.py` (só desenha).
  Bounds computados de TODOS os POIs para a moldura não pular a cada
  descoberta. O radar também mostra POIs descobertos (blips violeta; o fog é
  aplicado pelo chamador, e POIs `kind="station"` são filtrados para não
  duplicar o blip de estação).
- Regra do mundo (ADR 005): `ExplorationManager` criado em
  `_build_world_systems`, zerado em `_teardown_world`.

---

## Executar e testar

```bash
pip install pygame Pillow          # dependências
python main_pygame.py              # versão visual
SDL_VIDEODRIVER=dummy python main_pygame.py   # smoke headless (sem janela)

# Testes (cada um roda direto, sem framework):
python tests/test_docking.py
python tests/test_movement.py
python tests/test_boost.py             # boost de propulsor (ADR 007)
python tests/test_radar.py             # radar: projeção/clamp + relações (ADR 008)
python tests/test_supercruise.py       # supercruise: entrada/aceleração/drop seguro (ADR 010)
python tests/test_audio.py             # áudio por eventos: mapa/cooldown/tolerância (ADR 009)
python tests/test_exploration.py       # POIs/fog/descoberta/drop/cartografia (ADR 011)
python tests/test_starmap.py           # matemática do mapa: bounds/projeção/clamp (ADR 011)
python tests/test_cartography.py       # compra de cartografia na estação (pygame dummy)
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
  `shoot`, `dock_toggle`, `toggle_radar`, `supercruise_toggle`,
  `starmap_toggle`, `pause`.
- **Padrões:** W, S, A, D, Q, E, SHIFT, ESPAÇO, F, R, J, M, ESC.
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
    "boost": "left shift",
    "shoot": "space",
    "dock_toggle": "f",
    "toggle_radar": "r",
    "supercruise_toggle": "j",
    "starmap_toggle": "m",
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
| `"supercruise"` | Viagem rápida intra-setor; universo congelado exceto o player (ver ADR 010) |
| `"starmap"` | Mapa do setor com fog-of-war; jogo congelado como na pausa (ver ADR 011) |

Regras de transição importantes:
- O jogo **abre em `"main_menu"`**; o mundo só é construído em `start_new_game`
  ou `load_game`. `__init__` NÃO spawna player/NPCs/estações.
- A tecla de pausa (configurável) só abre o menu durante `"playing"`.
- ESC **nunca fecha o jogo diretamente** — sair exige "SAIR DO JOGO" no menu de pausa.
- Desacoplar (F no menu da estação) faz transição direta `"docked"` → `"playing"` sem ambiguidade.
- **Supercruise:** `"playing"` → spool-up (`_sc_spool > 0`, ainda em `"playing"`)
  → `"supercruise"`. Drop (automático por massa ou manual via `J`/ESC) volta a
  `"playing"`. ESC em supercruise **não** abre pausa — só dá drop. Não se entra
  perto de massa nem atracado/aproximando.
- **Starmap:** `M` em `"playing"` abre o mapa (`"starmap"`); `M`/ESC fecham de
  volta a `"playing"`. Sem branch de update — o mundo congela como na pausa.

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
