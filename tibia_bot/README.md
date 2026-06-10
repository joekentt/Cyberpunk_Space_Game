# EXP Bot — bot de hunt autônomo para OTServ (OTClient v8)

Bot de leveling 100% autônomo para servidores Tibia 10.x+ (TFS 1.x), escrito
como um **config Lua do módulo de bot embutido no [OTClient v8](https://github.com/OTCv8/otclientv8)**.
Ele roda *dentro* do cliente — sem leitura de tela, sem injeção de memória —
então funciona em qualquer resolução/SO e é estável.

> ⚠️ Use apenas no **seu próprio servidor** (ou onde bots sejam permitidos).

## O que ele faz sozinho

| Sistema | Comportamento |
|---|---|
| **Vocação** | Detecta a vocação do personagem logado e carrega o perfil certo (Knight / Paladin / Sorcerer / Druid, promovidas inclusas). |
| **Healbot** | Magias de cura em camadas (leve/forte/emergência) + poções de HP/mana, respeitando exhaust. |
| **Targeting** | Escolhe o alvo mais próximo (filtrável por nome), ataca, knight persegue (*chase*), paladin/magos mantêm distância e **kitam**. |
| **Magias de ataque** | exori/exori ico (knight, com contagem de monstros adjacentes para área), exori san/con (paladin), strikes (magos) — sempre reservando mana para a cura mais forte. |
| **Cavebot** | Loop de waypoints pela área de hunt, gravados in-game por botão. Lida com escadas/buracos e destrava sozinho. |
| **Looter** | Detecta a morte do alvo, anda até o corpo, abre e puxa os itens da lista (ou tudo). |
| **Refill** | Quando as poções/cap acabam: percorre a rota de refill, **deposita no banco** (`hi` → `deposit all` → `yes`) e **compra supplies no NPC** (`hi` → `trade` → compra via protocolo), depois volta ao waypoint de hunt mais próximo. |
| **Suporte** | Come comida, anti-idle (não cai por inatividade), modo emergência com HP crítico (para de andar/lootear, segue curando e revidando; logout opcional). |
| **Painel** | Status ao vivo (vocação, estado, exp/h) e botões de gravação de rota. |

## Instalação

1. Baixe e logue no seu servidor com o **OTClient v8** (otclientv8.com ou o
   release do GitHub). Configure o IP/porta do seu OT normalmente.
2. Abra o **bot** no cliente (ícone de robô / `Ctrl+Shift+B` em algumas builds).
3. Na janela do bot, clique no botão de **abrir a pasta de configs** (ícone de
   pasta). Copie a pasta **`EXP_Bot`** (de `tibia_bot/otcv8/`) para dentro dela.
4. De volta ao jogo, recarregue/selecione o config **EXP_Bot** na lista e ligue
   o bot. Os macros aparecem como switches; o painel **EXP** mostra o status.

Os arquivos carregam em ordem alfabética (`00_` → `08_`) e compartilham o
mesmo ambiente — não renomeie quebrando a ordem.

## Primeiro uso (5 minutos)

1. **Confira a vocação** no painel ("Vocação: knight" etc.). Se vier errada
   (vocations.xml fora do padrão), force em `01_config.lua`:
   `forceVocation = "knight"`.
2. **Grave a rota de caçada:** ande pelo respawn e clique **➕ WP caçada** a
   cada ~15–20 sqm (e em cada escada/buraco — coloque um WP *no degrau* e o
   próximo já no andar de destino). A rota é um **loop**: o último ponto deve
   estar perto do primeiro. Para cordas/alavancas, use **WP caçada: usar item**.
3. **Grave a rota de refill (opcional, mas recomendado):** começando de um
   ponto da hunt, ande até a cidade marcando **➕ WP refill**; pare ao lado do
   NPC do banco e clique **🏦 depositar**; pare ao lado do vendedor e clique
   **🧪 comprar supplies**; termine a rota de volta na entrada da hunt.
4. Pronto — solte o personagem e deixe upando. As rotas ficam salvas no
   storage do config (sobrevivem a relog).

## Configuração (`01_config.lua`)

- `attack.monsters` — lista de nomes para caçar; **vazia = ataca tudo**.
- `loot.items` — ids dos itens de loot (padrão: gold/platinum/crystal coin);
  `loot.everything = true` pega o corpo inteiro.
- `supplies.items` — regras de refill `{id, min, buyTo}`; vazia = o bot deriva
  das poções da sua vocação (mín. 5, compra até 60).
- `emergency` — HP% de pânico, HP% de retomada e logout opcional.
- `overrides` — ajusta o perfil da vocação sem mexer em `02_vocation.lua`
  (ex.: trocar a poção do knight para ultimate health `8473`).

Magias e poções padrão assumem o `spells.xml`/ids de item de um TFS 1.x
"vanilla" 10.x (health potion `7618`, mana `7620`, strong `7588`/`7589`,
great `7591`/`7590`, ultimate `8473`). Se o seu servidor customizou magias
(level/mana/palavras), ajuste o perfil em `02_vocation.lua` — é só dado.

## Arquitetura

```
00_compat.lua     única camada que toca a API do OTCv8 (tudo via Bot.*, com fallbacks)
01_config.lua     configuração do usuário (CFG)
02_vocation.lua   perfis por vocação + detecção automática (Profiles, Bot.profile)
03_healer.lua     curas/poções/emergência — roda sempre, nunca pausa
04_support.lua    comida + anti-idle
05_targeting.lua  alvo, chase/kite, magias de ataque
06_looter.lua     fila de corpos + coleta via onContainerOpen
07_cavebot.lua    waypoints hunt/refill, NPC de banco/compra, anti-stuck
08_panel.lua      painel de status e botões de gravação (todo em pcall)
```

Prioridade no loop: **curar > lutar > lootear > andar**. O cavebot só anda
quando não há alvo nem corpo pendente; a emergência congela tudo menos a cura
e o revide.

## Teste headless

`tibia_bot/tests/` traz um stub da API do OTCv8 e um teste de fumaça que roda
o bot inteiro sem cliente (cura, poção, targeting, loot, cavebot, refill e
emergência):

```bash
pip install lupa
python tibia_bot/tests/test_smoke.py
```

## Solução de problemas

- **Não cura / não ataca com magia:** a magia do seu OT difere (level, mana ou
  palavras). Edite o perfil em `02_vocation.lua`.
- **Não compra no NPC:** confira se o NPC abre loja com `trade` e vende os ids
  configurados. A compra usa `g_game.buyItem` direto no protocolo — o NPC
  precisa estar com a janela de trade aberta (a sequência `hi`/`trade` faz isso).
- **Vocação "desconhecida":** use `forceVocation` no `01_config.lua`.
- **Trava num obstáculo:** o anti-stuck dá passos aleatórios e pula o waypoint;
  se acontecer sempre no mesmo lugar, adicione waypoints mais próximos ali.
- **Painel não aparece:** sua build não expõe `UI.*` — o bot segue funcionando;
  os switches dos macros continuam na janela do bot.
