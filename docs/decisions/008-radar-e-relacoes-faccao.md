# ADR 008 — Radar de proximidade e fonte única de relações de facção

**Status:** Aceito  
**Data:** 2026-06-09

## Contexto

A consciência espacial do jogador era fraca: fora da viewport não havia como
saber o que estava ao redor. Um radar circular (estilo Elite) resolve isso lendo
posições que **já existem** (`universe.entities`, `station_mgr.get_all()`) e
desenhando blips relativos ao player. É puramente de apresentação — não toca
lógica de jogo.

Para colorir os blips por hostilidade, era preciso classificar a relação entre
facções. Essa informação já estava **duplicada** em dois lugares:
`CombatManager.hostility_table` (dict) e `NPCManager.HOSTILITY` (set). Criar uma
terceira cópia para o radar violaria o princípio de fonte única do projeto
(ver ADR 004).

## Decisão

### 1. Radar (`visual_engine/radar.py` + `radar_math.py`)

- Disco circular fixo no **canto inferior direito**, com o player no centro.
- Alcance configurável via `data/balance.json` → `radar.range` (padrão 2000 u).
- Blips **fora do alcance grudam na borda** (clamp) com brilho reduzido — dão
  direção sem poluir o disco.
- Cores por relação: **hostil = vermelho**, **neutro = amarelo**,
  **aliado = ciano**, **estação = verde (quadrado)**, **player = branco** no
  centro. Reutilizam o vocabulário visual do HUD de combate.
- **Norte do radar = +Y do mundo** (norte fixo, não alinhado à proa). Escolha
  deliberada por estabilidade: o disco não gira ao manobrar, então os blips não
  "deslizam".
- A matemática de projeção (`radar_project`) vive em `radar_math.py` **puro,
  sem pygame**, testável headless; a classe `Radar` só desenha.
- Toggle remapeável: ação `toggle_radar` (padrão `R`), estado `_radar_on`.

**Importante:** o alcance do radar **não** é o alcance de detecção da IA
(`ai.detection_range`). Ver um blip não significa que aquela nave já te detectou —
o radar é só ajuda de UX.

### 2. Fonte única de hostilidade (`systems/factions_util.py`)

Módulo puro com o set canônico `HOSTILITY` e dois helpers:

- `is_hostile(a, b)` — **direcional** `(atacante, alvo)`, preserva a semântica
  que a IA já usava.
- `relation(viewer, other)` — **simétrica**, devolve `"hostile"` / `"ally"` /
  `"neutral"` para coloração do radar.

`NPCManager` e `CombatManager` foram refatorados para derivar de `factions_util`
em vez de manter literais próprios (`NPCManager.HOSTILITY` virou alias;
`CombatManager.hostility_table` é derivado por compreensão). Comportamento
inalterado — coberto pelos testes de combate existentes.

## Alternativas consideradas

**Radar alinhado à proa (norte = direção da nave):** rejeitado. Mais imersivo,
mas os blips giram junto com a manobra, o que confunde a leitura rápida. Norte
fixo do mundo é mais estável e simples.

**Não fundir as tabelas de hostilidade (deixar o radar com a sua própria):**
rejeitado por violar fonte única (ADR 004). Três cópias divergiriam com o tempo.

**Radar como Surface alocada por blip:** rejeitado por desperdício. O radar
itera todas as entidades por frame; desenhar direto (sem alocar superfície por
blip) é trivial para algumas dezenas de entidades.

## Consequências

- Novos arquivos: `visual_engine/radar.py`, `visual_engine/radar_math.py`,
  `systems/factions_util.py`, `tests/test_radar.py`,
  `docs/decisions/008-radar-e-relacoes-faccao.md`.
- `main_pygame.py` instancia `self.radar` (persistente, como `HUD`/`Camera`),
  desenha no `_render` durante `"playing"`/`"paused"`, com toggle por tecla.
- `core/input_config.py`: ação `toggle_radar` (padrão `R`), remapeável.
- `data/balance.json` + `core/balance.py`: seção `radar` com `range`.
- Quando o Plano 06 introduzir corpos/objetos como entidades com `position`,
  o radar os inclui **automaticamente** (itera `universe.entities`).
- `tests/test_radar.py` cobre a matemática (projeção, clamp) e a classificação
  de relação **sem importar pygame**; testes de combate continuam passando.
