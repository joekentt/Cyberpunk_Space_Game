-- 02_vocation.lua
-- Perfis por vocação + detecção automática.
-- Cada perfil declara: curas (em ordem de gravidade), magias de ataque
-- (em ordem de prioridade), poções e postura (chase / manter distância).
--
-- Campos das magias:
--   words      palavras da magia
--   level      level mínimo para tentar
--   mana       custo de mana
--   below      (curas) lança quando HP% <= below
--   minTargets (ataques) nº mínimo de monstros adjacentes (magias de área)
--   range      (ataques) distância máxima do alvo

Profiles = {
    knight = {
        chase = true, keepDistance = 1,
        heals = {
            { words = "exura gran ico", level = 90, mana = 200, below = 40 },
            { words = "exura ico",      level = 8,  mana = 40,  below = 80 },
        },
        attacks = {
            { words = "exori gran", level = 90, mana = 340, minTargets = 3, range = 1 },
            { words = "exori",      level = 35, mana = 115, minTargets = 2, range = 1 },
            { words = "exori ico",  level = 16, mana = 30,  minTargets = 1, range = 1 },
        },
        potions = {
            hp   = { id = 7591, below = 45 },  -- great health potion
            mana = { id = 7589, below = 30 },  -- strong mana potion
        },
    },

    paladin = {
        chase = false, keepDistance = 3,
        heals = {
            { words = "exura gran san", level = 60, mana = 210, below = 40 },
            { words = "exura san",      level = 35, mana = 160, below = 70 },
            { words = "exura",          level = 8,  mana = 20,  below = 88 },
        },
        attacks = {
            { words = "exori san", level = 40, mana = 20, minTargets = 1, range = 4 },
            { words = "exori con", level = 23, mana = 25, minTargets = 1, range = 5 },
        },
        potions = {
            hp   = { id = 7588, below = 50 },  -- strong health potion
            mana = { id = 7589, below = 40 },  -- strong mana potion
        },
    },

    sorcerer = {
        chase = false, keepDistance = 3,
        heals = {
            -- exura vita p/ sorcerer existe no spells.xml padrão de muitos OTs;
            -- se o seu servidor negar, remova a linha ou use overrides no CFG.
            { words = "exura vita", level = 30, mana = 160, below = 45 },
            { words = "exura gran", level = 20, mana = 70,  below = 75 },
            { words = "exura",      level = 8,  mana = 20,  below = 90 },
        },
        attacks = {
            { words = "exori vis",  level = 12, mana = 20, minTargets = 1, range = 3 },
            { words = "exori flam", level = 14, mana = 20, minTargets = 1, range = 3 },
        },
        potions = {
            hp   = { id = 7618, below = 45 },  -- health potion
            mana = { id = 7620, below = 60 },  -- mana potion
        },
    },

    druid = {
        chase = false, keepDistance = 3,
        heals = {
            { words = "exura vita", level = 30, mana = 160, below = 45 },
            { words = "exura gran", level = 20, mana = 70,  below = 75 },
            { words = "exura",      level = 8,  mana = 20,  below = 90 },
        },
        attacks = {
            { words = "exori frigo", level = 15, mana = 20, minTargets = 1, range = 3 },
            { words = "exori tera",  level = 13, mana = 20, minTargets = 1, range = 3 },
        },
        potions = {
            hp   = { id = 7618, below = 45 },  -- health potion
            mana = { id = 7620, below = 60 },  -- mana potion
        },
    },
}

-- Detecção: o protocolo 10.x envia o "client id" da vocação
-- (vocations.xml: knight=1, paladin=2, sorcerer=3, druid=4; promovida = +10).
local CLIENT_VOC = { [1] = "knight", [2] = "paladin", [3] = "sorcerer", [4] = "druid" }

local cached, cachedAt = nil, 0

function Bot.profile()
    if not Bot.ready() then return nil end
    if cached and Bot.now() - cachedAt < 5000 then return cached end

    local name = CFG.forceVocation
    if not name then
        local ok, voc = pcall(function() return Bot.lp():getVocation() end)
        voc = (ok and voc) or 0
        name = CLIENT_VOC[voc % 10]
    end

    local base = name and Profiles[name]
    if not base then
        cached, cachedAt = nil, Bot.now()
        return nil
    end

    -- cópia rasa + overrides do CFG (sem mutar o perfil original)
    local prof = { name = name }
    for k, v in pairs(base) do prof[k] = v end
    for k, v in pairs(CFG.overrides[name] or {}) do prof[k] = v end

    cached, cachedAt = prof, Bot.now()
    return prof
end

-- mana que NUNCA deve ser gasta em ataque (reserva para a cura mais forte)
function Bot.manaReserve(prof)
    local reserve = 0
    for _, h in ipairs(prof.heals or {}) do
        if Bot.level() >= h.level and h.mana > reserve then reserve = h.mana end
    end
    return reserve
end

-- regras de supply efetivas: CFG.supplies.items ou derivadas das poções do perfil
function Bot.supplyRules()
    if #CFG.supplies.items > 0 then return CFG.supplies.items end
    local prof = Bot.profile()
    if not prof or not prof.potions then return {} end
    local rules = {}
    if prof.potions.hp then
        table.insert(rules, { id = prof.potions.hp.id, min = 5, buyTo = 60 })
    end
    if prof.potions.mana then
        table.insert(rules, { id = prof.potions.mana.id, min = 5, buyTo = 60 })
    end
    return rules
end
