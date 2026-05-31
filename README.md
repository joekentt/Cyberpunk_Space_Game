# Cyberpunk Space RPG

RPG espacial 2D top-down com geração procedural de naves, sistema de facções, IA de NPCs e combate tático com gestão de energia (W-S-E).

## Estrutura

```
Cyberpunk_Space_Game/
├── core/                # EventBus, SaveManager, InputConfig, GameLoop, DataLoader
├── systems/             # Managers (player, npc, combat, station, energy, economy...)
├── entities/            # Ship, Module, Station (dataclasses puras, sem pygame)
├── visual_engine/       # Sprites procedurais, HUD, Camera, StationUI, KeybindsUI
├── data/                # ships.json, factions.json, mission_templates.json
├── config/              # keybinds.json (gerado em runtime — não versionado)
├── saves/               # slots de save (gerados em runtime — não versionados)
├── tests/               # testes headless executáveis diretamente
├── main_pygame.py       # entry-point visual (Pygame)
└── main.py              # entry-point console
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

> As teclas abaixo são os **padrões**. Todas são remapeáveis pelo jogador
> em **ESC → CONFIGURAR TECLAS** sem reiniciar o jogo.

| Tecla padrão | Ação |
|---|---|
| W | Acelerar / aumentar throttle (motor principal, para frente) |
| S | Frear e engatar ré (diminuir throttle; ponto morto no centro) |
| A / D | Girar o bico esquerda / direita |
| Q / E | Strafe lateral esquerda / direita (thrusters RCS, sem girar o bico) |
| ESPAÇO | Disparar arma primária |
| **F** | **Acoplar em estação (dentro do raio) / Desacoplar** |
| 1 / 2 / 3 | Realocar 1 pip para Weapons / Shields / Engines |
| ESC | Abrir menu de pausa |

> **Empuxo:** motor principal (frente) é o mais forte; ré ~55% e strafe ~45%
> da força frontal. Toda a potência escala com os pips de **Engines**.

### Menu de pausa (ESC)

| Opção | Efeito |
|---|---|
| CONTINUAR | Fecha o menu e volta ao jogo |
| CONFIGURAR TECLAS | Abre a tela de remapeamento de keybinds |
| SAIR DO JOGO | Encerra o programa |

### Configurar Teclas

| Tecla | Ação |
|---|---|
| ↑ ↓ | Navegar entre as ações |
| ENTER | Iniciar rebind da ação selecionada (próxima tecla pressionada vira o novo bind) |
| ESC | Cancelar rebind em andamento / voltar ao menu de pausa |
| BACKSPACE | Restaurar todos os binds para o padrão |
| Clique do mouse | Selecionar ação e iniciar rebind |

Conflitos (duas ações na mesma tecla) são destacados em vermelho com aviso.
Os binds são salvos automaticamente em `config/keybinds.json`.

### Controles dentro de uma estação

| Tecla | Ação |
|---|---|
| ↑ ↓ | Navegar opções / lista de naves |
| ENTER | Confirmar / Comprar |
| ESC | Voltar à tela anterior |
| F | Desacoplar (do menu principal) |

## Loop de gameplay atual

1. Você começa com a **Skiff Mk I** e **50.000 cr** no espaço próximo à **Hub Alpha**
2. Aproxime de uma estação até entrar no raio (anel verde aparece) e pressione **F** para acoplar
3. Dentro da estação: **mercado de naves** (compra troca sprite e stats imediatamente) e **reparo grátis**
4. Voe livremente com o sistema de empuxo vetorial (frente, ré, strafe lateral)
5. Atire em piratas Wasp com ESPAÇO; gerencie energia com pips 1/2/3
6. Se sua nave for destruída: **respawn após 3 s** na última estação atracada, com a Skiff Mk I de volta e **-10% dos créditos**

## Testes

Cada teste é executável diretamente sem nenhum framework. A partir da raiz do projeto:

```bash
# Lógica pura (não dependem de pygame):
python tests/test_docking.py        # ciclo de docking, mercado, respawn
python tests/test_movement.py       # strafe, ré, hierarquia de empuxo
python tests/test_input_config.py   # keybindings: padrões, persistência, conflitos

# Outros testes:
python tests/test_foundation.py     # EventBus + GameLoop + DataLoader
python tests/test_missions.py       # geração e ciclo de missões
python tests/test_procedural.py     # geração de universo
python tests/test_visual_sprites.py # gera PNGs de naves em /tmp/space_rpg_sprites/
python tests/test_visual_preview.py # gera um frame preview do jogo
```

## Sistema de input (keybindings)

O mapeamento ação → tecla é configurável e persistido em `config/keybinds.json`
(criado automaticamente no primeiro rebind; ignorado pelo git).

O módulo `core/input_config.py` (`InputConfig`) é puro — sem pygame — e portanto
testável headless. Lê e grava com escrita atômica (`.tmp` + `os.replace`). Se o
arquivo não existir ou estiver corrompido, os padrões são usados silenciosamente.

Veja `CLAUDE.md` para detalhes de arquitetura e instruções para adicionar novas ações.

## Sistema de geração procedural de sprites

O `visual_engine/sprite_generator.py` gera naves 2D top-down determinísticas a partir de:

- `ship_class` (`Small` / `Medium` / `Large`) → perfil de silhueta
- `faction` (`United Humans` / `Orcs` / `Marth` / `Pirates` / `Independent`) → paleta
- `seed` (int) → variações controladas (mesma seed sempre produz o mesmo sprite)

Cada sprite tem 9 camadas: sombra, casco escuro, casco principal, highlight superior, linhas de painel, hardpoints, cockpit emissivo, motores com glow, contorno final.

Para adicionar uma nova classe de nave: edite `SHIP_PROFILES` em `sprite_generator.py`.
Para adicionar uma nova facção: edite `palettes` em `palette_manager.py`.

## Status

- ✅ Arquitetura modular: EventBus, GameLoop, DataLoader, SaveManager, InputConfig
- ✅ PlayerManager: throttle (frente/ré estilo Elite), strafe lateral (RCS), pips de engines
- ✅ EnergyManager (W-S-E), NPCManager (FSM chase/escort/flee/attack)
- ✅ CombatManager: projéteis, hit detection, dano a escudos/casco
- ✅ StationManager: docking, mercado de naves, reparo, respawn
- ✅ Menu de pausa com CONTINUAR / CONFIGURAR TECLAS / SAIR DO JOGO
- ✅ Keybindings configuráveis pelo jogador com persistência em disco
- ✅ Geração procedural de universo e sprites (3 classes × 5 facções)
- ✅ Versão Pygame jogável: movimento vetorial, parallax, VFX, HUD, câmera
- ⚠️ `tests/test_factions.py` desatualizado (API antiga do FactionManager)

## Próximos passos sugeridos

1. Visualização de dano progressivo nos sprites (DamageStateRenderer)
2. Sons (módulo `audio_engine`)
3. Menu principal e tela de criação de piloto
4. Saves funcionais com persistência completa de estado de mundo
5. Mapa estelar / sistema de viagem entre setores
