# ADR 009 — Áudio como consumidor puro de eventos

**Status:** Aceito
**Data:** 2026-06-09

## Contexto

O jogo não tinha som. O README listava "Sons (módulo `audio_engine`)" como
próximo passo. O `EventBus` torna isso trivial: os managers já emitem eventos de
gameplay (`WEAPON_FIRED`, `PROJECTILE_HIT`, `SHIP_DESTROYED`, `DOCKED`,
`BOOST_ACTIVATED`, `MISSION_COMPLETED`, `GAME_COMPLETED`, `PIPS_CHANGED`). Um
`AudioManager` que só escuta esses eventos e toca sons adiciona muita sensação de
"jogo pronto" a custo baixo, **sem nenhum outro sistema precisar conhecê-lo**.

## Decisão

### Áudio é um consumidor puro de eventos

Nenhum manager emite "toque o som X". O `AudioManager` (`systems/audio_manager.py`)
mapeia **evento → som** (data-driven em `data/audio.json`) e se inscreve no bus.
Nenhuma linha de gameplay muda.

### Tolerante a falhas (essencial)

No mesmo espírito do `InputConfig`/`balance`:
- Se `pygame.mixer` não inicializar (CI headless, laptop sem device), o
  `AudioManager` marca `enabled = False`, **não carrega samples** e continua se
  inscrevendo no bus de forma inócua. O jogo roda **em silêncio, sem crashar**.
- Se um arquivo de som faltar, aquela entrada é ignorada no load (sem crash); o
  resto toca normalmente.
- Se `data/audio.json` faltar ou corromper, cai num mapa vazio silenciosamente.

### Divisão mixer (boot) × AudioManager (mundo)

- `pygame.mixer.init()` roda **uma vez** no boot do jogo (`SpaceRPGVisual.__init__`),
  dentro de try/except. Não bloqueia o boot se falhar.
- O `AudioManager` é criado **por mundo** (`_build_world_systems`, regra do
  ADR 005), logo após `bus._listeners.clear()`. Só carrega samples e se inscreve.
  Como o clear roda antes, **recriar o mundo (novo jogo 2×) não duplica sons**.
  É descartado em `_teardown_world`.

### Volume e cooldown data-driven

`data/audio.json` traz `master_volume` e, por evento, `file`/`volume`/`cooldown`.
O `cooldown` (s) opcional evita empilhar samples (ex.: tiros a 20/s não somam
um sample por frame). Tuning não exige editar código.

### Assets placeholder versionados

Não há arte de áudio final. `tools/gen_placeholder_sfx.py` gera 8 WAVs
sintéticos curtos (~114 KB no total) com **stdlib pura** (`wave`/`math`/`struct`,
sem numpy nem pygame). Esses placeholders **são versionados** em `assets/audio/`
para o jogo rodar com som "out of the box"; troca-se por arte final depois
(mesmos nomes de arquivo). Marcados como placeholder no `data/audio.json`.

### Injeção para testabilidade

O `AudioManager` aceita `play_fn` (default = tocar de verdade; no teste =
registrar chamadas) e `time_fn` (default = `time.monotonic`). Assim a lógica de
mapeamento e cooldown é testada **sem hardware de áudio**.

## Alternativas consideradas

**Managers chamando o áudio diretamente:** rejeitado — acoplaria todo sistema de
gameplay ao áudio. O bus já dá o desacoplamento de graça.

**Inicializar o mixer por mundo:** rejeitado — `mixer.init()` é caro e global;
fazer uma vez no boot e só carregar samples por mundo é mais limpo.

**Não versionar placeholders (exigir arte antes de ter som):** rejeitado —
travaria o sistema atrás de arte. Placeholders sintéticos pequenos destravam e
ficam testáveis já.

## Consequências

- Novos: `systems/audio_manager.py`, `data/audio.json`,
  `tools/gen_placeholder_sfx.py`, `assets/audio/*.wav` (placeholders),
  `tests/test_audio.py`, este ADR.
- `main_pygame.py`: `pygame.mixer.init()` no boot; `AudioManager` criado em
  `_build_world_systems` e zerado em `_teardown_world`.
- `set_master_volume()`/`toggle_mute()` já existem no manager para uma futura UI
  de settings.
- Som de combate/docking/missão/boost toca quando há device; silêncio limpo sem
  device. `tests/test_audio.py` cobre tolerância a falhas, cooldown, mapa e
  ausência de duplicação — tudo headless.
