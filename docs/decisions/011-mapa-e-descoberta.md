# ADR 011 — Mapa estelar, fog-of-war e descoberta de zonas (Escopo A)

**Status:** Aceito
**Data:** 2026-06-09

## Contexto

O jogo visual roda em **um espaço único** com 3 estações fixas. O
`systems/universe_generator.py` gera sistemas estelares procedurais, mas o
`main_pygame` **não os consome** (código órfão para o mundo visual). Um "mapa
com zonas a descobrir" exige decidir entre dois escopos muito diferentes —
e essa decisão determina toda a arquitetura subsequente.

## Decisão central: Escopo A (mapa de um setor), não B (galáxia)

- **Escopo A (adotado):** o jogo continua em um único espaço contínuo (um
  "setor"), maior, com mais pontos de interesse (POIs). O mapa é uma tela que
  mostra esse setor; fog-of-war esconde POIs não descobertos. Não há viagem
  entre sistemas — o supercruise (ADR 010) basta para cruzar o setor.
  **Menor risco, reusa tudo que existe.**
- **Escopo B (adiado):** galáxia multi-sistema consumindo o
  `universe_generator`, com jump drive. É praticamente um novo pilar de jogo:
  muda save, spawn, economia e missões (todas hoje assumem um espaço só).
  **Só depois que A estiver sólido.** Quando vier, será um ciclo próprio com
  seus próprios ADRs (persistir sistema atual no save, recriar mundo por
  sistema via `_build_world_systems`, jump drive com recurso/cooldown).

## Decisões de arquitetura

### POIs são entidades de DADOS, separadas das `Ship`

`entities/poi.py` define `PointOfInterest` (`id, name, kind, position,
discovered, data`), com `kind ∈ {"station", "asteroid_field", "signal",
"derelict"}`. POIs **não entram** em `universe.entities` — não poluem o
universo de combate com objetos não-naves. O `ExplorationManager`
(`systems/exploration_manager.py`) é o dono do conjunto.

Neste ciclo os POIs são **visuais/navegacionais** (aparecem no mapa e no radar
quando descobertos), **sem presença física no mundo** — campos de asteroides
não têm sprites nem colisão, e mineração fica fora de escopo (a spec de
Naves/Roles prevê Miner como trabalho futuro).

### Estados iniciais de descoberta

As **3 estações começam descobertas** (o piloto conhece os hubs da região);
todo o resto começa oculto. Estações são registradas automaticamente como POIs
(`kind="station"`) pelo setup do mundo.

### Fog-of-war é por-POI (booleano), não por-célula

`discovered: bool` por POI. Grade de névoa contínua é mais bonita, mas mais
cara e desnecessária para validar o loop de descoberta. Fica para depois.

### Três canais de descoberta

1. **Proximidade:** `ExplorationManager.update(dt, player_pos)` marca POIs
   dentro de `discover_radius` e emite `POI_DISCOVERED` (uma única vez por
   POI). Funciona também **durante o supercruise** (cruzar o setor revela o
   que estiver no caminho — recompensa exploração).
2. **Drop de dados de localização:** naves destruídas podem soltar
   `location_data` (chance em `balance.exploration`), que revela **um** POI
   oculto aleatório (integra com `LootManager`).
3. **Cartografia na estação:** opção na `StationUI` que debita créditos
   (fonte única: `player.credits`, padrão do `_buy_ship`) e emite
   `CARTOGRAPHY_PURCHASED`; o `ExplorationManager` revela N POIs.

O payload de `POI_DISCOVERED` carrega `source` (`"proximity"` /
`"location_data"` / `"cartography"`) para o feedback visual diferenciar.

### Tela de mapa (`"starmap"`)

Novo `game_state == "starmap"` (tecla remapeável `starmap_toggle`, padrão
`M`), com o jogo **congelado** (como o menu de pausa). A matemática de
projeção mundo→mapa vive em `visual_engine/starmap_math.py` (**pura, sem
pygame**, testável headless); `starmap_ui.py` só desenha. Os limites do mapa
são computados de **todos** os POIs (não só descobertos) para a moldura não
"pular" a cada descoberta — isso não vaza informação além do tamanho do setor.

### Persistência aditiva (sem bump de versão)

`build_save_payload` ganha o campo opcional `exploration`
(`{"discovered_ids": [...]}`). Saves antigos carregam com `.get(...، {})` —
default = estado inicial (só estações descobertas). IDs desconhecidos no save
são ignorados. Segue o padrão do campo `progression` (Ciclo E).

### Regra do mundo (ADR 005)

O `ExplorationManager` é criado em `_build_world_systems` (após o
`bus._listeners.clear()`) e zerado em `_teardown_world` — recriar o mundo não
duplica listeners.

## Alternativas consideradas

**Escopo B agora:** rejeitado (risco alto; ver acima).

**POIs como entidades no `universe.entities`:** rejeitado — IA, combate e
radar iteram esse dict assumindo naves; objetos de dados puros lá dentro
exigiriam `isinstance` espalhado.

**Fog por célula de grade:** rejeitado neste ciclo (complexidade sem validar
o loop primeiro).

**Descoberta apenas por proximidade:** rejeitado — drop e cartografia criam
sinergias com combate e economia, e dão usos novos a sistemas existentes
(loot, estação) por custo baixo.

## Consequências

- Novos: `entities/poi.py`, `systems/exploration_manager.py`,
  `visual_engine/starmap_math.py`, `visual_engine/starmap_ui.py`,
  `tests/test_exploration.py`, `tests/test_starmap.py`,
  `tests/test_cartography.py`.
- Tocados: `main_pygame.py`, `core/input_config.py`, `core/balance.py`,
  `data/balance.json` (seção `exploration`), `systems/loot_manager.py`,
  `systems/game_state_serializer.py`, `visual_engine/station_ui.py`,
  `visual_engine/radar.py` (blips de POI descobertos).
- O radar (ADR 008) ganha blips de POI descobertos automaticamente — POIs têm
  `position`, como previsto lá.
- Faseamento incremental: Fase 1 (modelo + proximidade) → Fase 2 (starmap) →
  Fase 3 (drop) → Fase 4 (cartografia), cada uma com teste headless verde
  antes da próxima.
