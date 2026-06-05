# ADR 006 — Condição de vitória e Tier 2

**Data:** 2026-06-04
**Status:** Aceito

## Contexto

Até o Ciclo D o jogo não tinha fim: o jogador podia acumular créditos, comprar
naves e enfrentar piratas indefinidamente, mas não havia um objetivo de longo
prazo que desse sensação de conclusão. O Ciclo E fecha esse arco.

Havia três candidatos naturais para condição de vitória:

1. **Cadeia de bounties** — completar N missões BOUNTY (já existem templates,
   `record_kill`, `MISSION_COMPLETED`).
2. **Acumulação de créditos** — atingir C créditos. Simples, mas não usa as
   mecânicas de combate e missão.
3. **Eliminar um alvo especial** — nave chefe única. Requer entidade scripted
   nova e lógica de spawn fora do escopo deste ciclo.

## Decisão

### 1. Condição de vitória: 5 bounties completadas

Completar `WIN_BOUNTY_COUNT = 5` missões do tipo BOUNTY é a condição de
vitória. Motivos:

- **Reutiliza sistemas existentes** sem reimplementar nada: `MissionManager`
  já emite `MISSION_COMPLETED` com `type = "BOUNTY"`.
- **Força progressão de nave**: cada bounty exige abater NPCs; nave mais
  potente (Tier 2) reduz o tempo de cada bounty de forma perceptível.
- **Número calibrado para uma sessão de ~20-30 min** com naves T1 (cada
  bounty pede 1-3 kills), e ~10-15 min com T2.

`ProgressionManager` (`systems/progression_manager.py`) ouve
`MISSION_COMPLETED`, incrementa `bounties_completed`, e ao atingir o limite
emite `GAME_COMPLETED` uma única vez (`game_completed = True` bloqueia
re-emissão). O `SpaceRPGVisual` ouve `GAME_COMPLETED` e transita para o
estado `"endgame"`.

### 2. Tier 2 de naves

Dois modelos Tier 2 já existiam no catálogo (`stingray_raider`, 58 k cr;
`terraformador_ligeiro`, 110 k cr) mas nenhuma estação os vendia. Com este
ciclo:

| Estação | Facção | Inventário T2 |
|---|---|---|
| Hub Alpha | United Humans | terraformador_ligeiro |
| Hub Beta | Independent | stingray_raider |
| Posto Fronteira (nova) | Pirates | stingray_raider, terraformador_ligeiro |

A **Posto Fronteira** fica em [2600, 400] — além do território de patrulha
pirata inicial, incentivando o jogador a se aventurar além. A barreira de
acesso às naves T2 é exclusivamente de créditos (preços 58–110 k contra 50 k
iniciais), sem sistema de reputação de acesso (fora de escopo neste ciclo).

### 3. Tela de fim de jogo (`EndgameUI`)

Estado novo `"endgame"` com epílogo narrativo e duas opções:

- **CONTINUAR** — fecha a tela, volta a `"playing"` (o jogador pode continuar
  acumulando naves/créditos sem penalidade).
- **VOLTAR AO MENU** — chama `_go_main_menu()`.

`ESC` também aciona CONTINUAR (mantém o padrão de ESC nunca fechar o jogo
diretamente).

### 4. Persistência de progressão

`ProgressionManager.get_save_data()` / `load_save_data()` expõem
`{"bounties_completed": int, "game_completed": bool}`. O `build_save_payload`
recebe o dict via parâmetro `progression=`. É campo **aditivo**: saves antigos
sem o campo carregam com 0 bounties e `game_completed = False`.

Carregar um save com `game_completed = True` **não** reemite `GAME_COMPLETED`
(o flag é restaurado diretamente, o ProgressionManager bloqueia a emissão ao
detectar que já está completo).

### 5. HUD de progresso

Uma linha fixa no canto inferior esquerdo exibe `OBJETIVO: N/5 bounties`
(verde ao completar). Fica acima das linhas de missão ativa existentes.

## Consequências

### Positivas
- Fim de jogo claro, alcançável em ~30 min de jogo casual.
- Tier 2 tem papel funcional: 1.9× a ofensiva da Skiff acelera bounties
  de forma perceptível (ver ADR 004 sobre achatamento de curva).
- Progressão completamente testável headless (`tests/test_progression_v1.py`).
- Saves antigos (Ciclos C/D) continuam carregando sem erro.

### Negativas / limites deste ciclo
- Win condition é linear (completar N bounties), não ramificada — deliberado
  para manter escopo.
- Multi-slot de save fica para depois (só slot único).
- NPCs T2 (piratas Stingray como spawns) não foram adicionados — o jogador
  pode comprar T2 mas os inimigos continuam sendo Wasps Tier 1.

## Implementação
- `systems/progression_manager.py` (novo): `ProgressionManager`, `WIN_BOUNTY_COUNT = 5`.
- `visual_engine/endgame_ui.py` (novo): `EndgameUI`.
- `systems/game_state_serializer.py`: parâmetro `progression=` em `build_save_payload`.
- `main_pygame.py`: ciclo de vida, estado `"endgame"`, HUD de progresso,
  `_setup_stations` com Posto Fronteira, save/load de progressão.
- `tests/test_progression_v1.py` (novo): 4 critérios de aceitação.
