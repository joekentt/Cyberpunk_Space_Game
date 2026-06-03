# ADR 005 — Moldura de entrada (menu principal) e ciclo de vida do mundo

**Data:** 2026-06-03
**Status:** Aceito

## Contexto

Até o Ciclo C, `SpaceRPGVisual.__init__` entrava direto em `game_state =
"playing"` e já spawnava player, NPCs e estações. Não havia menu principal nem
criação de piloto: o arco de entrada do jogo estava aberto. O Ciclo D fecha esse
arco.

Dois problemas precisavam de decisão explícita:

1. **Quando o mundo é construído.** Se o init spawna o mundo, não há como abrir
   num menu "antes do jogo". Era preciso inverter: abrir no menu e só construir o
   mundo ao escolher "novo jogo" ou "carregar".
2. **A armadilha do EventBus singleton.** O `bus` (`core/event_bus.py`) é global
   e os managers se inscrevem no `__init__`. Recriar managers a cada novo jogo
   sem limpar acumularia **listeners duplicados** — cada `ADD_CREDITS`,
   `SHIP_DESTROYED` etc. dispararia N vezes após N partidas.

## Decisão

### 1. O jogo abre no menu principal; o mundo é construído sob demanda

`__init__` cria apenas o que é **persistente** (tela, fontes, configuração de
teclas, `SaveManager`, dados estáticos, UIs, visual de fundo) e seta
`game_state = "main_menu"`. **Não** spawna mundo.

- `start_new_game(pilot_name)` constrói o mundo do zero e entra em `"playing"`.
- `load_game(slot)` reconstrói o mundo e aplica o save por cima (reusa o
  serializer do Ciclo C — não reimplementa serialização).

Novos estados: `"main_menu"`, `"pilot_creation"`, `"load_menu"` (além dos já
existentes). Três UIs novas seguem o padrão de `KeybindsUI`/`StationUI`
(`handle_event`/`draw`, navegação ↑↓/ENTER/ESC): `MainMenuUI`,
`PilotCreationUI`, `LoadMenuUI`.

### 2. Fonte única de (re)construção + limpeza do bus

Todo (re)nascimento do mundo passa por `_build_world_systems()`, que:

1. `bus._listeners.clear()` — **limpa o bus antes** de qualquer coisa;
2. recria os managers de gameplay (que se reinscrevem no `__init__`);
3. re-inscreve os handlers de `self` via `_subscribe_self()`.

`_teardown_world()` (ao "SALVAR E SAIR PARA O MENU") também limpa o bus e zera os
managers para `None`. Resultado: **exatamente um listener por evento**, não
importa quantas partidas se inicie na mesma sessão. Garantido por
`tests/test_menu_flow.py` (item 4: dois `start_new_game` seguidos → um único
`ADD_CREDITS` processado).

Por que limpar o bus inteiro (e não desinscrever seletivamente): é simples,
robusto e centralizado. Como **todos** os assinantes são recriados a cada mundo
(managers + handlers de `self` + `VFXGenerator`), limpar tudo e reconstruir não
deixa pontas soltas. Desinscrição seletiva exigiria rastrear cada par
(evento, callback) — mais código e mais chances de erro.

### 3. Nome do piloto entra no save (serializer v2)

O payload de save ganha `pilot: {"name": str}` e `saved_at: float`
(`SAVE_VERSION` 1 → 2). São campos **aditivos**; o load usa `.get` com default,
então saves v1 continuam carregáveis. O menu de carregar exibe nome do piloto,
créditos e data.

## Consequências

### Positivas
- Arco de entrada fechado: menu → criar piloto → jogar; ou menu → carregar.
- Sem listeners duplicados ao reentrar (a armadilha do singleton é tratada num
  único lugar).
- `start_new_game`/`load_game` são testáveis headless (`SDL_VIDEODRIVER=dummy`),
  separando lógica de estado da renderização.
- Caminho pronto para multi-slot (a `LoadMenuUI` já lista entradas por slot).

### Negativas / limites deste ciclo
- **Slot único** ainda (multi-slot e CRUD de saves ficam para depois).
- Criação de piloto captura só o **nome** (sem facção/cor) — deliberado, o
  critério pede nome; a UI já está estruturada para crescer.
- NPCs não são persistidos: um jogo carregado recria os encontros padrão de NPC
  (consistente com o escopo do save no Ciclo C).

## Implementação
- `main_pygame.py`: init sem mundo; `_build_world_systems` / `_subscribe_self` /
  `_teardown_world`; `start_new_game` / `load_game` / `_go_main_menu`;
  roteamento e render por estado; opção de pausa "SALVAR E SAIR PARA O MENU".
- `visual_engine/main_menu_ui.py`, `pilot_creation_ui.py`, `load_menu_ui.py` (novos).
- `systems/game_state_serializer.py`: payload v2 com `pilot` e `saved_at`.
- `tests/test_menu_flow.py` (novo): boot no menu, novo jogo, round-trip de
  save/load e anti-listener-duplicado.
