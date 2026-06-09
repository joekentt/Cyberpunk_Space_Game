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

## Fluxo de entrada

O jogo **abre no menu principal** (não direto no gameplay):

| Opção | Efeito |
|---|---|
| NOVO JOGO | Abre a criação de piloto (digite um nome → começa o jogo) |
| CARREGAR JOGO | Lista os saves (nome do piloto, créditos, data) e carrega o escolhido. Só aparece se houver saves |
| CONFIGURAR TECLAS | Remapeamento de teclas (mesmo painel do menu de pausa) |
| SAIR | Encerra o programa |

## Progressão e objetivo de vitória

O jogo tem um objetivo de longo prazo: **completar 5 missões BOUNTY**. O
progresso aparece no HUD (`OBJETIVO: N/5 bounties`) durante o jogo.

Ao atingir 5 bounties, o jogo exibe a tela de conclusão com epílogo e duas
opções:

| Opção | Efeito |
|---|---|
| CONTINUAR | Fecha o epílogo e volta ao jogo (pode continuar acumulando créditos/naves) |
| VOLTAR AO MENU | Volta ao menu principal |

### Tiers de nave

| Tier | Exemplos | Preço | Vendido em |
|---|---|---|---|
| T1 — Inicial | Skiff Mk I | grátis | spawn |
| T1 | Wasp, Albatross, Heavy Mule | 45–95 k cr | Hub Alpha, Hub Beta |
| **T2** | **Stingray Raider** | **58 k cr** | Hub Beta, Posto Fronteira |
| **T2** | **Terraformador** | **110 k cr** | Hub Alpha, Posto Fronteira |

O **Posto Fronteira** (facção Piratas, [2600, 400]) fica além das patrulhas
iniciais e concentra o inventário Tier 2 completo.

Navegação dos menus: `↑↓` navega, `ENTER` confirma, `ESC` volta. Na criação de
piloto, digite o nome (até 16 caracteres; vazio vira "Piloto") e `ENTER`.

## Controles (versão Pygame)

> As teclas abaixo são os **padrões**. Todas são remapeáveis pelo jogador
> em **ESC → CONFIGURAR TECLAS** sem reiniciar o jogo.

| Tecla padrão | Ação |
|---|---|
| W | Acelerar / aumentar throttle (motor principal, para frente) |
| S | Frear e engatar ré (diminuir throttle; ponto morto no centro) |
| A / D | Girar o bico esquerda / direita |
| Q / E | Strafe lateral esquerda / direita (thrusters RCS, sem girar o bico) |
| **SHIFT** | **Boost de propulsor (pico de aceleração ~2.6× por 0.8 s; consome capacitor)** |
| ESPAÇO | Disparar arma primária |
| **F** | **Acoplar em estação (dentro do raio) / Desacoplar** |
| 1 / 2 / 3 | Realocar 1 pip para Weapons / Shields / Engines |
| ESC | Abrir menu de pausa |

> **Empuxo:** motor principal (frente) é o mais forte; ré ~55% e strafe ~45%
> da força frontal. Toda a potência escala com os pips de **Engines**.
>
> **Boost:** empuxo frontal ~2.6× por 0.8 s. Consome 1 carga do capacitor (máx 3).
> O capacitor recarrega ~0.5/s (escala com pips de **Engines**). Cooldown 0.4 s
> após o pico. Não afeta ré nem strafe. Remapeável como todas as teclas.

### Menu de pausa (ESC)

| Opção | Efeito |
|---|---|
| CONTINUAR | Fecha o menu e volta ao jogo |
| SALVAR JOGO | Grava o estado no slot único |
| SALVAR E SAIR PARA O MENU | Salva e volta ao menu principal (sem fechar o jogo) |
| CONFIGURAR TECLAS | Abre a tela de remapeamento de keybinds |
| SAIR DO JOGO | Encerra o programa |

> Durante o jogo, **F9** recarrega o último save (atalho de debug).

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
python tests/test_save_load.py      # save/load completo: nave, créditos, missões, reputação
python tests/test_menu_flow.py      # menu principal, criação de piloto, novo/carregar jogo
python tests/test_progression_v1.py # progressão e condição de vitória (Ciclo E)
python tests/test_factions.py       # reputação multi-eixo, market/dock, flags, persistência
python tests/test_universe_ai.py    # FSM da IA: IDLE→CHASE→ATTACK→FLEE

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

## Status — v1.0

- ✅ Arquitetura modular: EventBus, GameLoop, DataLoader, SaveManager, InputConfig
- ✅ PlayerManager: throttle (frente/ré estilo Elite), strafe lateral (RCS), pips de engines
- ✅ EnergyManager (W-S-E), NPCManager (FSM chase/escort/flee/attack)
- ✅ CombatManager: projéteis, hit detection, dano a escudos/casco
- ✅ StationManager: docking, mercado de naves, reparo, respawn
- ✅ Menu principal + criação de piloto (nome) + carregar jogo (ver ADR 005)
- ✅ Menu de pausa: CONTINUAR / SALVAR / SALVAR E SAIR PARA O MENU / TECLAS / SAIR
- ✅ Keybindings configuráveis pelo jogador com persistência em disco
- ✅ Save/load completo: nave, créditos, missões, reputação, piloto, progressão (ver ADR 003)
- ✅ Geração procedural de universo e sprites (3 classes × 5 facções, 6 modelos)
- ✅ **Tiers de nave**: T1 (Skiff, Wasp, Albatross, Heavy Mule) + T2 (Stingray Raider, Terraformador)
- ✅ **Condição de vitória**: completar 5 bounties → epílogo de fim de jogo (ver ADR 006)
- ✅ **ProgressionManager**: rastreia objetivo, persiste no save, não reemite ao carregar
- ✅ Versão Pygame jogável: movimento vetorial, parallax, VFX, HUD, câmera
- ✅ Suíte de testes headless cobrindo facções multi-eixo e FSM da IA (atualizados)

## Próximos passos sugeridos

1. Visualização de dano progressivo nos sprites (DamageStateRenderer)
2. Sons (módulo `audio_engine`)
3. Múltiplos slots de save com gerenciamento (deletar/renomear)
4. NPCs Tier 2 (Stingrays piratas como spawns de elite)
5. Mapa estelar / sistema de viagem entre setores
