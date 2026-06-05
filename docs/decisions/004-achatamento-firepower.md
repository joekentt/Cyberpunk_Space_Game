# ADR 004 — Achatamento da curva de poder de fogo e balanceamento data-driven

**Data:** 2026-06-03
**Status:** Aceito

## Contexto

O poder de fogo por disparo era derivado dos hardpoints com a fórmula
`firepower = small*1 + medium*3 + large*9`, dando Skiff x2, Wasp x7, Mule x4,
Albatross x1. A curva era **íngreme demais para o Tier 1**: a Wasp causava 3,5×
o dano da Skiff por tiro — e ainda dispara no mesmo cooldown. Na prática, comprar
a Wasp não era "uma melhoria perceptível", era um salto que tornava o duelo
inicial trivial de um lado e injusto do outro.

Além disso, todos os números de balanceamento (pesos da fórmula, alcances e
cadência da IA, recarga de escudo) estavam **hardcoded**, espalhados por
`combat_manager.py`, `npc_manager.py` e `energy_manager.py`, com a fórmula de
firepower ainda **duplicada** no painel de mercado (`station_ui.py`). Tuning
exigia editar código em vários lugares e arriscava dessincronizar.

## Decisão

### 1. Achatar a curva com pesos menores + compressão por expoente

```
raw       = small*1 + medium*2 + large*4
firepower = raw ** 0.6              (fallback 1.0 se sem hardpoint de arma)
```

O expoente `0.6` comprime a progressão. Resultado:

| Nave | raw | firepower | vs Skiff |
|---|---|---|---|
| Skiff (2S) | 2 | x1.52 | 1.00× |
| Wasp (4S+1M) | 6 | x2.93 | **1.93×** |
| Stingray (3S+1M) | 5 | x2.63 | 1.73× |
| Mule (1S+1M) | 3 | x1.93 | 1.27× |
| Albatross / Terraformador (1S) | 1 | x1.00 | 0.66× |

A melhor nave de combate Tier 1 (Wasp) fica em **1.93×** a ofensiva da Skiff —
dentro do alvo de 1.8–2.5× e bem abaixo dos 3.5× anteriores. O **fallback 1.0**
para naves sem arma é mantido (coberto por `tests/test_hardpoints.py`).

Por que expoente em vez de só trocar pesos: só com pesos 1/2/4 a razão
Wasp/Skiff ainda seria 3.0×. A compressão `^0.6` puxa o topo da curva para perto
da base sem inverter a ordem nem zerar diferenças, e é trivial de tunar (um único
número).

### 2. Mover os números para `data/balance.json` (data-driven)

Criado `core/balance.py` (singleton `balance`, **tolerante a falhas** como o
`InputConfig`: usa `DEFAULTS` se o arquivo faltar/corromper). Seções extraídas:
`firepower` (pesos, expoente, fallback), `ai` (alcances, `fire_chance_per_tick`,
limiares de flee/recover) e `shield` (`base_recharge`). Tuning de balanceamento
deixa de exigir edição de código.

A fórmula passou a ter **fonte única**: `CombatManager.firepower_from_hardpoints`.
O `station_ui.py` agora chama esse helper em vez de recalcular — fim da
duplicação.

### 3. Piratas Tier 1 lutam até o fim (`flee_shield_threshold = 0`)

NPCs não recarregam escudo (não têm `EnergyManager`). Com o threshold antigo de
20, o pirata fugia ao perder o escudo e **nunca mais voltava** (a recarga jamais
o levava de volta acima de 50), desengajando de forma permanente e inofensiva —
o duelo 1v1 virava trivial (o player saía ileso). Zerar o threshold torna os
piratas agressivos e o duelo um custo real. O `recover_shield_threshold` é
mantido no arquivo para NPCs futuros que voltem a lutar.

### 4. Recarga de escudo respeita `max_shields`

`EnergyManager` recarregava até `100` fixo. Trocado por `ship.max_shields`, para
não sobrecarregar naves de escudo menor (Wasp 80) nem subcarregar as maiores.

## Stats de nave (`data/ships.json`)

Após o achatamento + correção da recarga, a calibração por simulação
(`tests/test_combat_balance.py`) mostrou o duelo já justo **sem** alterar
`base_stats`: a Skiff (80 HP / 100 escudo) vence o pirata Wasp em ~3.6 s
perdendo, em média, ~67/180 de defesa (escudo, às vezes casco). Por isso os
stats do catálogo foram **mantidos** — o desbalanço vinha da curva de firepower e
da recarga, não dos HP/escudo. (Número de cadência ajustado:
`fire_chance_per_tick` 0.04 → 0.022, para 2 Wasps não deletarem a Skiff antes de
~4 s — ver item 4 do Ciclo B.)

## Consequências

### Positivas
- Upgrade de nave é perceptível (~1.9×) sem ser esmagador.
- Duelo Skiff vs pirata é vencível **com esforço** e disputado (validado por
  `tests/test_combat_balance.py`, faixas X=2 s / Y=25 s / Z=3 s).
- Tuning sem editar código; fórmula sem duplicação.

### Negativas / limites
- O `FLEE` por escudo fica efetivamente desligado para as naves atuais (todas
  sem recarga de escudo). É uma escolha de balanceamento de Tier 1, não um
  sistema novo; reabilitável via `data/balance.json`.
- `test_combat_balance.py` simula um piloto de **mira perfeita**; mede a moldura
  de balanceamento, não a skill real do jogador.

## Implementação
- `data/balance.json` (novo) + `core/balance.py` (novo, singleton tolerante).
- `combat_manager.py`: `firepower_from_hardpoints` (fórmula data-driven, fonte
  única) + `hardpoint_firepower` delega a ele.
- `npc_manager.py` / `energy_manager.py`: lêem parâmetros do `balance`.
- `station_ui.py`: usa o helper do `CombatManager` (sem duplicar fórmula).
- `tests/test_hardpoints.py`: atualizado para a nova curva.
- `tests/test_combat_balance.py` (novo): duelos 1v1 e 2v1 com a IA real.
