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

-- Detecção: o protocolo envia o id da vocação. Convenção real do Tibia/RubinOT
-- (vocations.xml padrão): 1=sorcerer, 2=druid, 3=paladin, 4=knight; as
-- PROMOVIDAS são 5–8 (master sorcerer / elder druid / royal paladin / elite
-- knight). Alguns datapacks usam base+10 — o `% 10` cobre esse caso também.
local CLIENT_VOC = {
    [1] = "sorcerer", [2] = "druid", [3] = "paladin", [4] = "knight",
    [5] = "sorcerer", [6] = "druid", [7] = "paladin", [8] = "knight",
}

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

-- mana que NUNCA deve ser gasta em ataque (reserva para a cura mais forte).
-- Em modo "trust" não confiamos no custo das magias do servidor, então a
-- reserva vira uma fração da mana máxima (CFG.manaReservePercent).
function Bot.manaReserve(prof)
    if (CFG.castGating or "trust") == "trust" then
        local maxm = 0
        pcall(function() maxm = Bot.lp():getMaxMana() or 0 end)
        return math.floor(maxm * (CFG.manaReservePercent or 0.30))
    end
    local reserve = 0
    for _, h in ipairs(prof.heals or {}) do
        if Bot.level() >= h.level and h.mana > reserve then reserve = h.mana end
    end
    return reserve
end

-- ---------- maquinário de cast tolerante a servidor desconhecido ----------
-- Em "strict": só lança se level/mana baterem (TFS vanilla).
-- Em "trust" : lança e verifica se a mana caiu; se não caiu (level insuficiente,
--              mana, cooldown ou magia inexistente no servidor), põe a magia em
--              backoff por 20 s e o chamador tenta a próxima da lista.
Bot.casting = { groupNext = {}, backoff = {}, pending = nil }

-- group: "heal" (cooldown ~1 s) ou "attack" (~2 s); grupos independentes.
function Bot.tryCast(words, group, level, mana)
    local now = Bot.now()
    local c = Bot.casting
    group = group or "heal"
    if c.backoff[words] and now < c.backoff[words] then return false end
    if c.groupNext[group] and now < c.groupNext[group] then return false end

    if (CFG.castGating or "trust") == "strict" then
        if Bot.level() < (level or 0) then return false end
        if Bot.mana() < (mana or 0) then return false end
    elseif Bot.mana() < 1 then
        return false
    end

    local before = Bot.mana()          -- capturado ANTES do say (mana ainda não caiu)
    Bot.say(words)
    c.groupNext[group] = now + (group == "attack" and 2000 or 1000)
    c.pending = { words = words, manaBefore = before, at = now }
    return true
end

-- chamado uma vez por tick (pelo healer): fecha a verificação do último cast
function Bot.verifyCasts()
    local p = Bot.casting.pending
    if not p or (Bot.now() - p.at) < 300 then return end
    if Bot.mana() >= p.manaBefore then
        -- mana não caiu → o cast falhou; evita spammar essa magia por um tempo
        Bot.casting.backoff[p.words] = Bot.now() + 20000
    end
    Bot.casting.pending = nil
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
