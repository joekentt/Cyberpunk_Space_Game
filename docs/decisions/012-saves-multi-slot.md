# ADR 012 — Múltiplos slots de save com metadados derivados

**Status:** Aceito
**Data:** 2026-06-12

## Contexto

O jogo salvava num slot único (`SAVE_SLOT = 1`), embora o `SaveManager` já
fosse parametrizado por slot e a `LoadMenuUI` estivesse "preparada para
multi-slot". O Bloco F pede 3 slots com gerenciamento: ver o que há em cada um
(piloto, créditos, progresso, data), salvar/carregar no slot escolhido e
deletar — sem quebrar saves existentes.

## Decisão

### Metadados DERIVADOS, não duplicados (formato inalterado)

O payload v2 (`game_state_serializer`) **já contém** tudo que a UI de slots
precisa: `pilot.name`, `credits` (fonte única), `saved_at` e
`progression.bounties_completed/game_completed`. Decidimos **não** adicionar
um bloco de metadados redundante ao payload (que poderia divergir da fonte de
verdade): `SaveManager.save_metadata(slot)` lê o arquivo e **deriva** o
cabeçalho leve:

```python
{"slot", "version", "pilot_name", "credits", "saved_at",
 "progress": {"bounties_completed", "game_completed"}}
```

Sem mudança de formato ⇒ **sem bump de versão** (continua `version: 2`) e
retro-compatibilidade de graça.

### Política de migração de versão

Não há migração de arquivo: campos ausentes caem em **defaults no load**
(mesmo padrão aditivo dos ADRs anteriores). Um save v1 (sem `pilot`,
`saved_at`, `progression`) lista como `"Piloto"`, sem data, 0 caçadas — e
carrega normalmente, pois `apply_save_payload` já usa `.get` com default em
todos esses campos. `save_metadata` é tolerante: slot vazio ou JSON corrompido
→ `None` (a UI mostra "— vazio —"), nunca exceção.

### Uma UI de slots, dois modos

A `LoadMenuUI` foi estendida em vez de criar uma `SaveMenuUI` paralela
(mesmas linhas, mesma navegação — duplicar seria divergência garantida):

- `open(entries, mode="load"|"save")` — o main monta SEMPRE `NUM_SLOTS` (3)
  entradas via `save_metadata` (slots vazios incluídos).
- **load:** ENTER em slot preenchido → `("load", slot)`; vazio é inerte.
- **save:** ENTER em slot vazio → `("save", slot)`; em slot ocupado abre
  **confirmação de sobrescrita** (ENTER/Y confirma, ESC/N cancela).
- **DEL/BACKSPACE** em slot preenchido (ambos os modos) → confirmação →
  `("delete", slot)`. Quem deleta de fato é o main (`save_mgr.delete_save`),
  que então reabre a lista atualizada.

### Estado `"save_menu"` e o slot ativo da sessão

"SALVAR JOGO" na pausa abre a seleção de slot (novo `game_state`
`"save_menu"`, mundo congelado como na pausa, overlay escuro). ESC volta a
`"paused"`; salvar volta a `"playing"`.

`self.current_slot` rastreia o slot "ativo" (setado ao salvar ou carregar).
"SALVAR E SAIR PARA O MENU" e o F9 de debug usam esse slot — fluxo rápido sem
passar pela tela de slots, mas sempre apontando para onde o jogador
salvou/carregou por último. Default: slot 1.

## Alternativas consideradas

**Bloco de metadados embutido no payload:** rejeitado — duplicaria
piloto/créditos (risco de divergência com a fonte única do ADR 003) para
economizar uma leitura de JSON que é barata na escala de 3 slots.

**Arquivo de índice (`saves/index.json`):** rejeitado — segunda fonte de
verdade que pode dessincronizar do diretório (delete manual, copy de save).
Listar pelo filesystem é o que o `SaveManager` já fazia.

**`SaveMenuUI` separada:** rejeitado — 90% idêntica à `LoadMenuUI`; um campo
`mode` resolve.

## Consequências

- `core/save_manager.py`: + `delete_save(slot)` (seguro, retorna bool),
  + `save_metadata(slot)` (cabeçalho leve, tolerante), + `_slot_path`.
  Escrita atômica intocada.
- `visual_engine/load_menu_ui.py`: modos load/save, slots vazios,
  confirmações de sobrescrita/delete.
- `main_pygame.py`: `NUM_SLOTS = 3`, estado `"save_menu"`, `current_slot`,
  `_save_entries()` via `save_metadata`.
- `tests/test_save_multislot.py`: 3 slots distintos + metadados, load por
  slot, delete isolado, retro-compat v1. `test_menu_flow` ajustado ao novo
  contrato de `_save_entries` (3 linhas).
- Renomear slot ficou de fora (opcional no bloco; o nome do piloto já
  identifica o save).
