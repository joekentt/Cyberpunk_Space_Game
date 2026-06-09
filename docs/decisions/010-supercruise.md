# ADR 010 — Supercruise (viagem rápida intra-setor)

**Status:** Aceito
**Data:** 2026-06-09

## Contexto

Viajar entre estações distantes (Hub Alpha `[400,400]`, Hub Beta `[1600,900]`,
Posto Fronteira `[2600,400]`) no empuxo normal (~150 u/s de cruzeiro) é
monótono. O Elite resolve com *supercruise*: um modo de voo de altíssima
velocidade onde a distância "encolhe", com drop automático ao se aproximar de
massa — preservando a tensão de combate (sem teleporte).

Este é o primeiro sistema que interage com vários outros (combate, docking,
spawn, câmera), então o desenho de estados e as regras de entrada/saída são o
ponto crítico. Sem cuidado, supercruise vira teleporte e mata o combate.

## Decisão

### Supercruise é um `game_state` novo (`"supercruise"`)

Não é um modificador do voo normal — é um ramo separado da máquina de estados de
`SpaceRPGVisual.game_state`. Nesse estado:

- **Universo congelado, exceto o player.** Não rodam `universe.update`,
  `npc_mgr.update`, `combat_mgr.update` nem `station_mgr.update`. NPCs não se
  movem nem engajam; projéteis não colidem; docking não dispara. A consequência:
  **sem dano ao player e sem combate** durante a viagem.
- Só a **rotação** está ativa (mira a proa); o resto do voo é governado pelo
  `SupercruiseManager`.

### Velocidade escalonada, não teleporte

O `SupercruiseManager` acelera o player ao longo da proa (`accel`) até
`max_speed` (padrão 6000 u/s, ~40× o cruzeiro normal). A câmera segue
normalmente, dando sensação de viagem. A posição é integrada por frame
(`player.apply_physics`) — **nunca** se pula posição instantaneamente.

### Drop por massa (regra central)

Ao chegar a `drop_radius` (320 u) de qualquer estação, o jogo força a saída e
reposiciona o player a `exit_offset` (260 u) da estação, na linha de onde a nave
veio. Como **`exit_offset` (260) > maior `docking_radius` (180) + folga**, o
player **nunca acopla sozinho** ao sair — recria o "interdiction-free arrival"
do Elite. (Coberto explicitamente por `tests/test_supercruise.py`, caso 5.)

### Entrada manual com spool-up

Tecla remapeável `supercruise_toggle` (padrão `J`) inicia um **spool-up** de
`spool_up_s` (2 s) antes de entrar — não é instantâneo, e é **cancelável**
(apertar de novo durante a carga aborta). Não se entra perto de massa
(`min_entry_distance`, mesma checagem que aborta o spool se uma massa se
aproximar) nem atracado/em aproximação.

### Saída

- **Automática:** drop por massa (acima).
- **Manual:** apertar `supercruise_toggle` **ou ESC** dá drop imediato no local
  atual. ESC aqui **não** abre pausa nem fecha o jogo — mantém o princípio
  "ESC nunca fecha o jogo" (ADR 005).

Em ambos os casos a velocidade de viagem é atenuada (×0.02) para um arrasto
controlável e emite-se `SUPERCRUISE_DROP` (VFX/áudio futuros podem escutar).

### Sem custo de recurso neste ciclo

Escopo deliberadamente enxuto: supercruise não consome combustível/energia.
Pode ganhar custo num ADR futuro (limite documentado).

## Alternativas consideradas

**Supercruise como modificador do voo normal (sem game_state):** rejeitado.
Misturaria a física de viagem com a de combate no mesmo branch, dificultando
garantir "sem dano durante a viagem". Um estado separado é mais simples e seguro.

**Teleporte instantâneo entre estações:** rejeitado — mata a tensão e a
exploração. A viagem escalonada preserva a sensação de espaço.

**ESC = pausa durante supercruise:** rejeitado. Mais intuitivo é ESC = sair do
supercruise (drop), consistente com "ESC nunca fecha o jogo".

## Consequências

- Novo arquivo `systems/supercruise_manager.py` — **lógica pura, sem pygame nem
  game_state** (só faz contas), reutilizável quando o Plano 06 (multi-setor)
  chegar: o manager é agnóstico a "setor".
- `main_pygame.py`: novo branch de update e de render, helpers
  `_toggle_supercruise_spool`/`_tick_supercruise_spool`/`_drop_supercruise`,
  overlay de túnel (estrelas alongadas) + HUD de viagem (velocidade, distância
  ao alvo, "DROP EM Xs", "DROP IMINENTE").
- `core/input_config.py`: ação `supercruise_toggle` (padrão `J`), remapeável.
- `data/balance.json` + `core/balance.py`: seção `supercruise` data-driven.
- `tests/test_supercruise.py`: lógica do manager headless (entrada, aceleração,
  integração, drop por massa, segurança do drop, idempotência).
- O voo normal, o docking e o combate **não foram alterados** — testes de
  movimento/combate/docking continuam passando.

### Nota de balanceamento

`drop_radius` (320) precisa ser maior que qualquer `docking_radius` (180) +
margem, senão o player atravessaria a estação antes do drop. `exit_offset` (260)
precisa ser maior que `docking_radius` para não auto-acoplar. Ambos vivem em
`data/balance.json` e podem ser tunados sem editar código.
