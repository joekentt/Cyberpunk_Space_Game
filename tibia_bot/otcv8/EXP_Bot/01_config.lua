-- 01_config.lua
-- ÚNICO arquivo que você precisa editar no dia a dia.
-- IDs de item abaixo são os padrões de servidores 10.x (TFS 1.x).
--
-- SERVIDOR RUBINOT-LIKE: os IDs de poção e o level/mana das magias podem
-- diferir do padrão. Não precisa adivinhar: ligue o bot, clique em
-- "🔍 Inspecionar" no painel e veja no console a sua vocação + os IDs reais
-- dos seus itens. Preencha aqui só o que estiver diferente. O modo de cast
-- "trust" (abaixo) já faz o bot funcionar mesmo sem você acertar level/mana.

CFG = {

    -- ===================== CAST (compat. servidor customizado) =====================
    -- "trust"  → tenta lançar a magia e AUTO-DESCOBRE o que dá: se a mana não
    --            cair, coloca a magia em backoff (20 s) e usa a de baixo.
    --            Ideal para RubinOT-like, onde não sabemos level/mana exatos.
    -- "strict" → só lança se level/mana do perfil baterem (TFS vanilla).
    castGating = "trust",
    -- Em modo "trust", fração da mana máxima sempre reservada para CURA
    -- (não gasta em ataque). 0.30 = guarda 30% da mana para se curar.
    manaReservePercent = 0.30,

    -- ===================== ALVOS =====================
    attack = {
        -- Lista de monstros para caçar. VAZIA = ataca QUALQUER monstro.
        -- Ex.: monsters = {"Rotworm", "Carrion Worm", "Cyclops"},
        monsters = {},
        range = 7,              -- só engaja monstros até N sqm de distância
        switchSlack = 3,        -- só troca de alvo se houver outro N sqm mais perto
    },

    -- ===================== CURA =====================
    -- Os gatilhos de magia/poção por vocação ficam em 02_vocation.lua.
    -- Aqui só o comportamento de emergência:
    emergency = {
        pauseBelowHp = 20,      -- HP% que ativa modo emergência (para cavebot/loot)
        resumeAboveHp = 60,     -- HP% para voltar ao normal
        tryLogout = false,      -- true = tenta logout seguro durante a emergência
    },

    -- ===================== LOOT =====================
    loot = {
        enabled = true,
        everything = false,     -- true = pega TUDO do corpo (cuidado com a cap)
        duringCombat = false,   -- true = abre corpos mesmo com monstro na tela
        maxDistance = 5,        -- desiste de corpos a mais de N sqm
        items = {               -- ids 10.x
            2148,               -- gold coin
            2152,               -- platinum coin
            2160,               -- crystal coin
        },
    },

    -- ===================== COMIDA =====================
    food = { 2671, 2666, 2789 }, -- ham, meat, brown mushroom (tenta em ordem)

    -- ===================== SUPPLIES / REFILL =====================
    supplies = {
        minCap = 80,            -- abaixo desta capacidade (oz) → refill
        -- Regras de supply. VAZIA = o bot gera regras automáticas a partir
        -- das poções da sua vocação (min 5, compra até 60).
        -- buyTo = quantidade alvo na hora de comprar no NPC.
        -- Ex.: { {id = 7620, min = 10, buyTo = 80}, {id = 7591, min = 5, buyTo = 40} },
        items = {},
    },

    -- ===================== VOCAÇÃO =====================
    -- O bot detecta a vocação sozinho. Se a detecção errar no seu servidor
    -- (vocations.xml com clientid fora do padrão), force aqui:
    -- "knight" | "paladin" | "sorcerer" | "druid"
    forceVocation = nil,

    -- Sobrescreve partes do perfil da vocação sem editar 02_vocation.lua.
    -- Ex.: overrides = { knight = { keepDistance = 1, potions = {...} } },
    overrides = {},
}
