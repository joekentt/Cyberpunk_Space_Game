# Cyberpunk Space RPG

RPG espacial 2D top-down com geração procedural de naves, sistema de facções, IA de NPCs e combate tático com gestão de energia (W-S-E).

## Estrutura

```
space_rpg/
├── core/                # EventBus, GameLoop, SaveManager, DataLoader
├── systems/             # Managers (combat, economy, faction, mission, NPC, AI...)
├── entities/            # Ship, Module, Mission (dataclasses puras)
├── visual_engine/       # PaletteManager, SpriteGenerator, ProceduralAssembler,
│                        # VFX, Camera, HUD — geração procedural de pixel art
├── data/                # ships.json, factions.json, mission_templates.json
├── tests/               # Suite de testes do projeto
├── assets/              # (vazio) reservado para assets futuros
├── saves/               # (vazio) gerado em runtime pelos saves
├── main.py              # Entry-point versão console (HUD em texto)
└── main_pygame.py       # Entry-point versão visual (Pygame)
```

## Setup

Requisitos: Python 3.10+ e duas bibliotecas:

```bash
pip install pygame Pillow
```

## Executar

**Versão visual (Pygame):**
```bash
python main_pygame.py
```

**Versão console (sem Pygame):**
```bash
python main.py
```

**Validação headless** (verifica que tudo importa e renderiza sem abrir janela):
```bash
SDL_VIDEODRIVER=dummy python main_pygame.py
```

## Controles (versão Pygame)

| Tecla | Ação |
|-------|------|
| W | Acelerar |
| A / D | Rotacionar esquerda / direita |
| ESPAÇO | Disparar arma primária |
| **F** | **Acoplar em estação (dentro do raio) / Desacoplar** |
| 1 / 2 / 3 | Realocar 1 pip para Weapons / Shields / Engines |
| ESC | Sair |

### Controles dentro de uma estação

| Tecla | Ação |
|-------|------|
| ↑ ↓ | Navegar opções / lista de naves |
| ENTER | Confirmar / Comprar |
| ESC | Voltar à tela anterior |
| F | Desacoplar (do menu principal) |

## Loop de gameplay atual

1. Você começa com a **Skiff Mk I** e **50.000 cr** no espaço próximo à **Hub Alpha**
2. Pode aproximar de uma estação até entrar no raio (anel verde aparece)
3. Pressionar **F** acopla — UI da estação abre com **mercado de naves** e **reparo grátis**
4. Comprar uma nave troca seu sprite e stats imediatamente
5. Voar livremente, atirar em piratas Wasp com ESPAÇO
6. Se sua nave for destruída: **respawn após 3s** na última estação atracada, com a **Skiff Mk I de volta** e **-10% dos créditos** (penalidade)

## Testes

Cada teste é executável diretamente. A partir da raiz do projeto:

```bash
python tests/test_foundation.py        # EventBus + GameLoop + DataLoader
python tests/test_missions.py          # geração e ciclo de missões
python tests/test_procedural.py        # geração de universo
python tests/test_visual_sprites.py    # gera PNGs de naves em /tmp/space_rpg_sprites/
python tests/test_visual_preview.py    # gera um frame preview do jogo
```

## Sistema de geração procedural de sprites

O `visual_engine/sprite_generator.py` gera naves 2D top-down determinísticas a partir de:

- `ship_class` (`Small` / `Medium` / `Large`) → perfil de silhueta
- `faction` (`United Humans` / `Orcs` / `Marth` / `Pirates` / `Independent`) → paleta
- `seed` (int) → variações controladas (mesma seed sempre produz o mesmo sprite)

Cada sprite tem 9 camadas: sombra, casco escuro, casco principal, highlight superior, linhas de painel, hardpoints, cockpit emissivo, motores com glow, contorno final.

Para adicionar uma nova classe de nave: edite `SHIP_PROFILES` em `sprite_generator.py` e defina os pontos do hemisfério superior do contorno (em coordenadas normalizadas), posição do cockpit, dos motores e dos hardpoints. O algoritmo espelha automaticamente o hemisfério inferior.

Para adicionar uma nova facção: edite `palettes` em `palette_manager.py` definindo `primary`, `primary_dark`, `primary_light`, `secondary`, `accent` e `glow`.

## Status conhecido

- ✅ Arquitetura modular, EventBus, GameLoop, DataLoader, SaveManager
- ✅ Sistemas: PlayerManager (com input via bus), EnergyManager (W-S-E),
  NPCManager (FSM com chase/escort/flee/attack), AIOrchestrator,
  FactionManager (reputação multi-eixo), MissionManager (procedural),
  LootManager, EconomyManager, EventManager (eventos dinâmicos),
  DialogueManager (bark + hook LLM)
- ✅ Geração procedural de universo (`universe_generator.py`)
- ✅ Geração procedural de sprites de naves (3 classes × 5 facções)
- ✅ Versão Pygame jogável (movimento, rotação, parallax, VFX, HUD)
- ⚠️ `tests/test_factions.py` foi escrito para uma versão antiga do
  `FactionManager` (procura `player_reputation`); precisa ser reescrito
  para usar `reputation_axes`. Bug não-bloqueante.

## Próximos passos sugeridos

1. Implementar combate visual: projéteis, hit detection, dano aos escudos/casco
2. Sistema de estações e docking (acoplar para comprar módulos, missões)
3. Visualização de dano progressivo nos sprites (DamageStateRenderer)
4. Sons (módulo `audio_engine` a criar)
5. Menu principal e tela de criação de piloto
6. Saves funcionais com persistência completa de estado de mundo
