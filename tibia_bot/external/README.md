# EXP Bot — Harness de QA por visão de tela (bot externo)

Ferramenta **externa** que captura a janela do cliente, lê o estado pela própria
interface (barras de HP/mana, battle list, minimapa, log) e age por
teclado/mouse — **sem ler memória e sem depender de arquivos do cliente**.
Funciona com cliente fechado de distro.

Foi feita para **QA do seu próprio servidor** (mapa global, oficial-like):
medir a curva de XP, **estimar o tempo até um level alvo** na dificuldade
natural, avaliar desempenho (freeze/lag, latência de reação) e **sinalizar
anomalias/bugs** com screenshot para revisão humana.

> ⚠️ Uso destinado ao **seu próprio servidor** (ou onde automação é permitida).
> Num servidor público que você não administra, isto viola regras e prejudica
> outros jogadores — não use.

## Como funciona (visão geral)

1. **Calibração:** você marca uma vez, num overlay, onde ficam as regiões da
   tela (viewport, barras, battle list, minimapa, XP, log). Salvo em
   `config/calibration.json`. Nada de pixel hardcoded.
2. **Ações pelas hotkeys do cliente:** você monta a rotação de cura/ataque nas
   **hotkeys do próprio cliente** (F1, F2…). O bot só lê o estado e aperta a
   tecla certa na condição certa → fica **vocação-agnóstico** automaticamente.
3. **Andar:** caçada por **waypoints clicados no minimapa** — usa o pathfinding
   do cliente no mapa global, então não precisa de dados de mapa.
4. **QA:** mede XP/h, ETA até o level alvo, detecta tela congelada e registra
   anomalias (travado, morte, disconnect) com screenshot. Gera um relatório
   por sessão em `runs/<data>/` (`report.json` + `series.csv`).

## Instalação (na máquina onde o cliente roda — Windows)

```bash
pip install -r requirements.txt
# OCR de XP/log exige o binário Tesseract instalado no sistema:
#   Windows: https://github.com/UB-Mannheim/tesseract/wiki
```

## Uso

```bash
python run.py            # abre o painel de controle
python run.py calibrate  # só (re)calibra as regiões da tela
```

No painel:

1. **① Calibrar regiões** — arraste um retângulo sobre cada região pedida.
2. Copie `config/profile.example.json` para `config/profile.json` e ajuste:
   - `heal_rules` — qual hotkey apertar abaixo de qual % de HP/mana.
   - `attack_next_key` / `attack_keys` — tecla de "atacar próximo" e a rotação
     de ataque (as magias/munição moram nas hotkeys do cliente).
   - `target_level` — o level até onde você quer medir o ETA.
3. **② Gravar waypoint** — posicione o mouse sobre o ponto do minimapa para onde
   quer andar e clique no botão (ou aperte **F9**). Repita para montar o loop da
   caçada.
4. **▶ Iniciar.** O status ao vivo mostra HP/mana, inimigos, **XP/h**, **ETA** e
   nº de anomalias. **Mouse no canto superior-esquerdo = ABORT** (failsafe).
5. **■ Parar** salva o relatório em `runs/<data>/`.

## Saídas de QA (`runs/<data>/`)

- `report.json` — tempo total, XP/h (sessão e janela), **ETA até o level alvo**,
  contagem e lista de anomalias.
- `series.csv` — série temporal (HP, mana, XP, inimigos) para você plotar a
  curva.
- `*.png` — screenshots automáticos de cada anomalia (freeze, morte, travado).

## Arquitetura

```
run.py                  entry point (abre o painel)
vision_bot/
  capture.py    captura de tela (mss) + assinatura de frame p/ freeze
  calibrate.py  overlay tkinter p/ marcar regiões → calibration.json
  inputs.py     teclado/mouse (pydirectinput) + failsafe; dry_run p/ ensaio
  state.py      lê HP/mana (fill da barra), battle list e alvo  [Pillow puro]
  ocr.py        OCR de XP e eventos do log (pytesseract)
  healer.py     aperta hotkeys de cura/poção por threshold
  combat.py     engaja inimigo + rodízio de hotkeys de ataque
  cavebot.py    waypoints no minimapa + detecção de travado
  qa.py         XP/h, ETA, FreezeDetector, AnomalyLog, SessionReport  [stdlib]
  controller.py loop principal: ler → curar → combater → andar + métricas
  panel.py      painel tkinter (start/pause/stop, calibrar, gravar waypoint)
tests/          headless, só Pillow + stdlib (rodam sem cliente)
```

Prioridade no loop: **curar > combater > andar**. As deps pesadas (mss, opencv,
pytesseract, pydirectinput) são importadas de forma preguiçosa, então os módulos
de lógica (`state`, `qa`) e os testes rodam só com Pillow + stdlib.

## Testes (headless, sem cliente)

```bash
python tests/test_state.py     # leitura de barras/battle list (imagens sintéticas)
python tests/test_qa.py        # XP/h, ETA, freeze, anomalias, relatório
python tests/test_behavior.py  # healer/combat/cavebot (Inputs dry_run + relógio injetado)
```

## Limitações (honestas)

- **Visão é sensível** a resolução/tema/escala da fonte → recalibre se mudar a
  UI. O OCR de XP depende da fonte; se falhar, o ETA fica "indeterminado" (o
  resto do bot continua).
- **Loot por visão não está na v1** — para QA de leveling, deixe o auto-loot do
  cliente ligado, se houver.
- O detector de bugs **sinaliza anomalias para revisão humana**; não prova
  ausência de bug.
- Comece **supervisionado**, com o dedo no abort, numa área fraca, e confira o
  primeiro `report.json` antes de soltar sessões longas.
