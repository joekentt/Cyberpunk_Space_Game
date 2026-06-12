-- 05_targeting.lua
-- Seleção de alvo, postura (chase × manter distância) e magias de ataque.
-- Continua ativo durante a emergência (revidar > fugir andando).

local lastChase = nil

local function wantedSet()
    local set = nil
    if #CFG.attack.monsters > 0 then
        set = {}
        for _, n in ipairs(CFG.attack.monsters) do set[n:lower()] = true end
    end
    return set
end

local function isWanted(creature, set)
    if not set then return true end
    return set[(creature:getName() or ""):lower()] == true
end

-- afasta um passo do alvo quando perto demais (paladin/mago)
local function kite(target, keep)
    local me, tp = Bot.pos(), target:getPosition()
    if not tp or Bot.dist(me, tp) >= keep then return end
    local sx = me.x > tp.x and 1 or (me.x < tp.x and -1 or 0)
    local sy = me.y > tp.y and 1 or (me.y < tp.y and -1 or 0)
    -- candidatos: diagonal de fuga, depois cada eixo
    local candidates = { {sx, sy}, {sx, 0}, {0, sy} }
    local DIR = {
        ["0,-1"] = 0, ["1,-1"] = 4, ["1,0"] = 1, ["1,1"] = 5,
        ["0,1"] = 2, ["-1,1"] = 6, ["-1,0"] = 3, ["-1,-1"] = 7,
    }
    for _, c in ipairs(candidates) do
        local dx, dy = c[1], c[2]
        if dx ~= 0 or dy ~= 0 then
            local dest = { x = me.x + dx, y = me.y + dy, z = me.z }
            if Bot.tileWalkable(dest) then
                Bot.step(DIR[dx .. "," .. dy])
                return
            end
        end
    end
end

macro(200, "Targeting", function()
    if not Bot.ready() or Bot.paused then return end
    local prof = Bot.profile()
    if not prof then return end

    local set = wantedSet()
    local me = Bot.pos()
    local mobs = {}
    for _, m in ipairs(Bot.monsters(CFG.attack.range)) do
        if isWanted(m, set) then table.insert(mobs, m) end
    end

    if #mobs == 0 then
        Bot.fighting = false
        return
    end
    Bot.fighting = true

    table.sort(mobs, function(a, b)
        local da, db = Bot.dist(me, a:getPosition()), Bot.dist(me, b:getPosition())
        if da ~= db then return da < db end
        return (a:getHealthPercent() or 100) < (b:getHealthPercent() or 100)
    end)

    -- ----- alvo atual: mantém se ainda for válido (histerese contra ping-pong) -----
    local target = g_game.getAttackingCreature()
    local valid = false
    if target and (target:getHealthPercent() or 0) > 0 and isWanted(target, set) then
        local tp = target:getPosition()
        if tp and tp.z == me.z and Bot.dist(me, tp) <= CFG.attack.range then
            local best = Bot.dist(me, mobs[1]:getPosition())
            valid = Bot.dist(me, tp) <= best + CFG.attack.switchSlack
        end
    end
    if not valid then
        target = mobs[1]
        pcall(function() g_game.attack(target) end)
    end

    local tpos = target:getPosition()
    Bot.lastTarget = {
        id = target:getId(),
        pos = tpos,
        name = target:getName(),
        hp = target:getHealthPercent() or 100,
    }

    -- ----- postura -----
    if prof.chase ~= lastChase then
        Bot.setChase(prof.chase)
        lastChase = prof.chase
    end
    if not prof.chase and tpos then
        kite(target, prof.keepDistance)
    end

    -- ----- magias de ataque -----
    if not tpos then return end

    local adjacent = 0
    for _, m in ipairs(mobs) do
        if Bot.dist(me, m:getPosition()) <= 1 then adjacent = adjacent + 1 end
    end
    local reserve = Bot.manaReserve(prof)   -- protege a mana de cura (abs. ou %)
    local targetDist = Bot.dist(me, tpos)

    for _, a in ipairs(prof.attacks or {}) do
        -- corpo a corpo (range 1): exige minTargets monstros adjacentes
        -- (magias de área); à distância: basta o alvo dentro do range
        local conditionMet = (a.range <= 1 and adjacent >= (a.minTargets or 1))
                or (a.range > 1 and targetDist <= a.range)
        -- nunca gasta a mana reservada para cura; level/mana exato e cooldown
        -- ficam a cargo do tryCast (respeita gating e backoff por magia)
        if conditionMet and Bot.mana() > reserve then
            if Bot.tryCast(a.words, "attack", a.level, a.mana + reserve) then break end
        end
    end
end)
