# ADR 007 — Boost de propulsor (capacitor dedicado)

**Status:** Aceito  
**Data:** 2026-06-09

## Contexto

O sistema de movimento era puramente linear: W acelera, S freia/ré, Q/E strafe.
Não havia mecânica de "pico de velocidade" que exigisse gestão de recursos, o que
tornava o combate previsível e eliminava decisões táticas sobre posicionamento.

## Decisão

Adicionamos um **boost de propulsor** remapeável (padrão: SHIFT), com as
seguintes propriedades:

- Injeta empuxo frontal equivalente a `thrust_power × force_mult` por `duration`
  segundos (padrão: 2.6× por 0.8 s).
- Consome `cost` unidades de um **capacitor dedicado** `boost_charge` (separado
  de `current_energy`). O capacitor tem `max_charge = 3` cargas e recarrega a
  `recharge_per_s = 0.5/s`, escalado pelo modificador de pips de engines.
- Um `cooldown = 0.4 s` após o pico impede spam; o jogador pode ter no máximo
  3 boosts consecutivos antes de precisar esperar.
- O boost **não afeta ré nem strafe** — apenas o vetor frontal do bico.
- Toda a implementação é remapeável via `InputConfig` (ação `"boost"`).

### Parâmetros (em `data/balance.json`, seção `boost`)

| Parâmetro | Valor | Significado |
|---|---|---|
| `force_mult` | 2.6 | Multiplicador de força frontal durante o boost |
| `duration` | 0.8 s | Duração do pico de empuxo |
| `cost` | 1.0 | Cargas consumidas por ativação |
| `max_charge` | 3.0 | Capacidade máxima do capacitor |
| `recharge_per_s` | 0.5 | Taxa de recarga base (escala com pips de engines) |
| `cooldown` | 0.4 s | Tempo após o pico até poder boostar de novo |

## Alternativas consideradas

**Boost como consumo de energia** (`current_energy`): rejeitado porque já existe
o sistema W-S-E de pips. Competir pelo mesmo recurso complicaria o balanceamento
e tornaria boost + shields mutuamente exclusivos de forma não divertida.

**Boost ilimitado com cooldown puro**: rejeitado porque remove a gestão de
recursos. Três boosts consecutivos antes de secar o capacitor criam uma janela
tática interessante.

**Boost afetando ré e strafe**: rejeitado por feedback confuso. O jogador espera
que SHIFT seja "mais frente", não "mais em todas as direções".

## Consequências

- `PlayerManager` expõe `try_boost()`, `_boost_timer`, `_boost_cd` e
  `boost_charge` com sincronização para `Ship` via `_sync_boost_to_ship()`.
- O HUD exibe uma barra "BOOST" abaixo dos pips W-S-E.
- Durante o boost, um segundo engine trail colorido (cor de acento da facção)
  é emitido via `VFXManager` para feedback visual imediato.
- O teste `tests/test_boost.py` cobre 6 casos headless: ativação, velocidade,
  isolamento de ré/strafe, cooldown, recarga e ausência de carga.
- Todos os parâmetros são data-driven: tuning não requer alteração de código.
